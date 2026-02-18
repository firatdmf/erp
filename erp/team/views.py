from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
from django.db import transaction
import json

from .models import Team, TeamMember, TeamTask, TeamMessage, TeamMeeting, FavoriteTeam, ChatRoom, TeamBoardColumn, TeamTaskHistory

def get_user_team(user):
    """Get the user's primary team (first team they belong to or created)"""
    team = user.teams.first()
    if not team:
        # Create default team for user
        team = Team.objects.create(
            name=f"{user.get_full_name()}'s Team",
            creator=user
        )
        TeamMember.objects.create(team=team, user=user, role='admin')
        # Create default chat room
        ChatRoom.objects.create(
            team=team,
            name='General',
            room_type='channel',
            created_by=user,
            is_default=True
        )
    return team

@login_required
def team_list(request):
    """Team Overview - Display all user's teams with cards"""
    filter_type = request.GET.get('filter', 'all')
    
    if filter_type == 'favorites':
        favorite_ids = FavoriteTeam.objects.filter(user=request.user).values_list('team_id', flat=True)
        teams = request.user.teams.filter(id__in=favorite_ids, is_archived=False)
    elif filter_type == 'archived':
        teams = request.user.teams.filter(is_archived=True)
    else:
        teams = request.user.teams.filter(is_archived=False)
    
    teams = teams.prefetch_related('member_objects__user', 'tasks')
    
    context = {
        'teams': teams,
        'filter': filter_type,
        'all_count': request.user.teams.filter(is_archived=False).count(),
        'page_title': 'Team Overview',
    }
    return render(request, 'team_list.html', context)

@login_required
def team_tasks(request):
    """Kanban task board with columns"""
    team_id = request.GET.get('team_id')
    if team_id:
        team = get_object_or_404(Team, id=team_id, members=request.user)
    else:
        team = get_user_team(request.user)
    
    if request.method == 'POST':
        try:
            # Support both 'title' (local modal) and 'name' (sidebar)
            title = request.POST.get('title') or request.POST.get('name')
            if not title:
                return JsonResponse({'success': False, 'error': 'Task title is required'})

            description = request.POST.get('description', '')
            due_date = request.POST.get('due_date') or None
            priority = request.POST.get('priority', 'medium')
            status = request.POST.get('status', 'todo')

            # Handle Team ID override from sidebar
            form_team_id = request.POST.get('team_id')
            if form_team_id:
                 team = get_object_or_404(Team, id=form_team_id)

            # Determine Target Users
            target_users = []
            assign_to_team = request.POST.get('assign_to_team') == 'on'
            assigned_users_str = request.POST.get('assigned_users', '')

            if assign_to_team:
                # All team members
                target_users = [tm.user for tm in TeamMember.objects.filter(team=team)]
            elif assigned_users_str:
                # Specific users
                user_ids = [uid for uid in assigned_users_str.split(',') if uid.strip()]
                target_users = User.objects.filter(id__in=user_ids)
            elif request.POST.get('assigned_to'):
                # Legacy/Single support
                try:
                    target_users = [User.objects.get(id=request.POST.get('assigned_to'))]
                except User.DoesNotExist:
                    pass
            
            if not target_users:
                 # Default to creator if no one assigned
                 target_users = [request.user]

            # Create Tasks
            # 1. Handle Attachments (Upload once)
            attachments_data = []
            if request.FILES.getlist('task_files'):
                from erp.google_drive import upload_file_to_drive
                
                for file_item in request.FILES.getlist('task_files'):
                    upload_result = upload_file_to_drive(request.user, file_item, folder_name="ERP Team Tasks")
                    if upload_result.get('success'):
                        attachments_data.append({
                            'name': upload_result.get('name'),
                            'file_id': upload_result.get('file_id'),
                            'drive_link': upload_result.get('drive_link')
                        })
                    else:
                        print(f"Failed to upload attachment {file_item.name}: {upload_result.get('error')}")

            # Get default 'To Do' column
            col_todo = TeamBoardColumn.objects.filter(team=team, title='To Do').first()
            if not col_todo:
                 col_todo = TeamBoardColumn.objects.create(team=team, title='To Do', color='blue', order=0)

            # 2. Create Task and Link Attachments
            # Create ONE task for all users (Shared Task)
            primary_assignee = target_users[0] if target_users else None
            
            task = TeamTask.objects.create(
                team=team,
                title=title,
                description=description,
                assigned_by=request.user,
                assigned_to=primary_assignee, # Legacy support
                due_date=due_date,
                priority=priority,
                status=status,
                column=col_todo
            )
            
            # Add all targets to ManyToMany field
            if target_users:
                task.assignees.set(target_users)
                
                # Send notifications to assignees
                from notifications.models import Notification
                for user in target_users:
                    if user.id != request.user.id and hasattr(user, 'member'):
                        Notification.create_notification(
                            recipient=user.member,
                            notification_type='task_assigned',
                            title=f'New Task: {task.title}',
                            message=f'You have been assigned to "{task.title}" by {request.user.get_full_name() or request.user.username}',
                            link=f'/team/task/{task.id}/',
                            icon='fa-tasks',
                            content_object=task
                        )

            from .models import TeamTaskAttachment
            for att_data in attachments_data:
                TeamTaskAttachment.objects.create(
                    task=task,
                    file_name=att_data['name'],
                    drive_file_id=att_data['file_id'],
                    drive_link=att_data['drive_link'],
                    uploaded_by=request.user
                )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Tasks created successfully'})
            
            return redirect('team:team_tasks')

        except Exception as e:
            print(f"Error creating team task: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # Ensure default columns exist
    columns = TeamBoardColumn.objects.filter(team=team).order_by('order')
    if not columns.exists():
        col_todo = TeamBoardColumn.objects.create(team=team, title='To Do', color='blue', order=0)
        col_inp = TeamBoardColumn.objects.create(team=team, title='In Progress', color='orange', order=1)
        col_rev = TeamBoardColumn.objects.create(team=team, title='Review', color='purple', order=2)
        col_done = TeamBoardColumn.objects.create(team=team, title='Done', color='green', order=3)
        columns = [col_todo, col_inp, col_rev, col_done]
        
        # Migrate existing tasks
        TeamTask.objects.filter(team=team, status='todo').update(column=col_todo)
        TeamTask.objects.filter(team=team, status='in_progress').update(column=col_inp)
        TeamTask.objects.filter(team=team, status='review').update(column=col_rev)
        TeamTask.objects.filter(team=team, status='done').update(column=col_done)
        TeamTask.objects.filter(team=team, status='completed').update(column=col_done)

    # Fetch tasks with columns
    # We will pass 'columns' to template, each column object will have a .tasks list attached
    
    # Fix for orphaned tasks (tasks with no column assigned)
    # This ensures older tasks appear on the board
    orphaned_tasks = TeamTask.objects.filter(team=team, column__isnull=True)
    if orphaned_tasks.exists():
        # Get columns (we know they exist by now)
        col_map = {c.title: c for c in columns}
        
        # Map status to column title
        status_map = {
            'todo': 'To Do',
            'in_progress': 'In Progress',
            'review': 'Review',
            'done': 'Done'
        }
        
        for status_code, col_title in status_map.items():
            if col_title in col_map:
                TeamTask.objects.filter(
                    team=team, 
                    column__isnull=True, 
                    status=status_code
                ).update(column=col_map[col_title])

    # Efficiently fetch all tasks and group them by column in python to avoid N+1
    # Efficiently fetch all tasks and group them by column in python to avoid N+1
    all_tasks = TeamTask.objects.filter(team=team).select_related('assigned_to', 'assigned_by', 'column').prefetch_related('assignees', 'attachments')
    
    # Attach tasks to columns
    # Re-query columns to be safe or use the list
    if isinstance(columns, list):
         pass # already list
    else:
         columns = list(columns)
         
    for col in columns:
        col.task_list = [t for t in all_tasks if t.column_id == col.id]

    # Get current user role
    current_member = TeamMember.objects.filter(team=team, user=request.user).first()
    user_role = current_member.role if current_member else 'member'

    context = {
        'team': team,
        'user_teams': request.user.teams.filter(is_archived=False), # Valid teams for switcher
        'members': TeamMember.objects.filter(team=team).select_related('user'),
        'columns': columns, # Pass columns instead of separate task lists
        'page_title': f'{team.name} Tasks',
        'user_role': user_role,
    }
    return render(request, 'team_tasks.html', context)

@login_required
@require_http_methods(["POST"])
def complete_task(request, task_id):
    """Mark task as completed"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permission
    if task.assigned_to != request.user and request.user != task.assigned_by:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    task.status = 'done'
    task.completed_at = timezone.now()
    task.save()
    
    return JsonResponse({'success': True, 'message': 'Task marked as completed'})

@login_required
@require_http_methods(["POST"])
def update_task_status(request, task_id):
    """Update task status (for Kanban drag-and-drop)"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check if user is team member
    # Check strict permissions for moving tasks
    # Allowed: Assignees, Creator, or Admin/Manager/Owner
    is_assignee = task.assignees.filter(id=request.user.id).exists()
    is_creator = task.assigned_by == request.user
    is_admin = TeamMember.objects.filter(team=task.team, user=request.user, role__in=['admin', 'manager', 'owner']).exists()

    if not (is_assignee or is_creator or is_admin):
        return JsonResponse({'success': False, 'error': 'You can only move your own tasks'}, status=403)
    
    new_status = request.POST.get('status')
    column_id = request.POST.get('column_id') # If client sends column_id
    
    if column_id:
        column = get_object_or_404(TeamBoardColumn, id=column_id, team=task.team)
        task.column = column
        # Map column to status for backwards compatibility if needed, or just keep status loosely active
        # For now, let's infer status from known titles or just leave it
        if column.title.lower() == 'done':
             task.status = 'done'
             task.completed_at = timezone.now()
        else:
             task.status = 'todo' # Default or map others
        task.save()

        # Log History
        TeamTaskHistory.objects.create(
            task=task,
            user=request.user,
            event_type='status_change',
            old_value='(Drag & Drop)',
            new_value=column.title
        )

        return JsonResponse({'success': True, 'message': f'Task moved to {column.title}'})

    # Legacy status update support (drag drop via data-status)
    valid_statuses = ['todo', 'in_progress', 'review', 'done']
    
    if new_status and new_status in valid_statuses:
        task.status = new_status
        # Try to find a column with this title
        # Map status to title mapping
        title_map = {
            'todo': 'To Do',
            'in_progress': 'In Progress',
            'review': 'Review',
            'done': 'Done'
        }
        target_title = title_map.get(new_status)
        if target_title:
             col = TeamBoardColumn.objects.filter(team=task.team, title=target_title).first()
             if col:
                 task.column = col
        
        if new_status == 'done':
            task.completed_at = timezone.now()
        task.save()

        # Log History
        TeamTaskHistory.objects.create(
            task=task,
            user=request.user,
            event_type='status_change',
            new_value=new_status
        )

        return JsonResponse({'success': True, 'message': f'Task status updated to {new_status}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid status or column'}, status=400)


@login_required
@require_http_methods(["POST"])
def create_section(request):
    """Create a new Kanban section/column"""
    team_id = request.POST.get('team_id')
    title = request.POST.get('title')
    color = request.POST.get('color', 'blue')
    
    team = get_object_or_404(Team, id=team_id)
    
    # Check permission
    if not TeamMember.objects.filter(team=team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
    if not title:
         return JsonResponse({'success': False, 'error': 'Title required'}, status=400)
         
    # Get max order
    max_order = TeamBoardColumn.objects.filter(team=team).aggregate(models.Max('order'))['order__max']
    order = 0 if max_order is None else max_order + 1
    
    TeamBoardColumn.objects.create(
        team=team,
        title=title,
        color=color,
        order=order
    )
    
    return JsonResponse({'success': True, 'message': 'Section created'})

@login_required
@require_http_methods(["POST"])
def edit_section(request, column_id):
    """Edit an existing Kanban section"""
    title = request.POST.get('title')
    color = request.POST.get('color')
    
    column = get_object_or_404(TeamBoardColumn, id=column_id)
    
    # Check permission
    if not TeamMember.objects.filter(team=column.team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
    if title:
        column.title = title
    if color:
        column.color = color
        
    column.save()
    return JsonResponse({'success': True, 'message': 'Section updated'})

def reorder_section(request):
    """Reorder Kanban sections"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
        
    import json
    try:
        data = json.loads(request.body)
        column_ids = data.get('column_ids', [])
        
        if not column_ids:
            return JsonResponse({'success': False, 'error': 'No data provided'}, status=400)

        # Update order for each column
        for index, col_id in enumerate(column_ids):
            TeamBoardColumn.objects.filter(id=col_id).update(order=index)
            
        return JsonResponse({'success': True, 'message': 'Order updated'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def create_task(request):
    """Create a new team task"""
    # Support both 'title' (local modal) and 'name' (sidebar)
    title = request.POST.get('title') or request.POST.get('name')
    if not title:
        return JsonResponse({'success': False, 'error': 'Task title is required'})

    try:
        description = request.POST.get('description', '')
        due_date = request.POST.get('due_date') or None
        priority = request.POST.get('priority', 'medium')
        status = request.POST.get('status', 'todo')

        # Handle Team ID override from sidebar
        form_team_id = request.POST.get('team_id')
        team = None
        if form_team_id:
            team = get_object_or_404(Team, id=form_team_id)
        else:
            # Fallback to user's team if not provided (though form should provide it)
            team = get_user_team(request.user)

        # Determine Target Users
        target_users = []
        assign_to_team = request.POST.get('assign_to_team') == 'on'
        assigned_users_str = request.POST.get('assigned_users', '')

        if assign_to_team:
            # All team members
            target_users = [tm.user for tm in TeamMember.objects.filter(team=team)]
        elif assigned_users_str:
            # Specific users
            user_ids = [uid for uid in assigned_users_str.split(',') if uid.strip()]
            target_users = User.objects.filter(id__in=user_ids)
        elif request.POST.get('assigned_to'):
            # Legacy/Single support
            try:
                target_users = [User.objects.get(id=request.POST.get('assigned_to'))]
            except User.DoesNotExist:
                pass
        
        if not target_users:
             # Default to creator if no one assigned
             target_users = [request.user]

        # Create Tasks
        # 1. Handle Attachments (Upload once)
        attachments_data = []
        if request.FILES.getlist('task_files'):
            from erp.google_drive import upload_file_to_drive
            
            for file_item in request.FILES.getlist('task_files'):
                upload_result = upload_file_to_drive(request.user, file_item, folder_name="ERP Team Tasks")
                if upload_result.get('success'):
                    attachments_data.append({
                        'name': upload_result.get('name'),
                        'file_id': upload_result.get('file_id'),
                        'drive_link': upload_result.get('drive_link')
                    })
                else:
                    print(f"Failed to upload attachment {file_item.name}: {upload_result.get('error')}")

        # Get default 'To Do' column
        col_todo = TeamBoardColumn.objects.filter(team=team, title='To Do').first()
        if not col_todo:
             # Fallback if no column exists (though view ensures it)
             col_todo = TeamBoardColumn.objects.create(team=team, title='To Do', color='blue', order=0)

        # 2. Create Tasks and Link Attachments
        # Create ONE task and add all assignees
        primary_assignee = target_users[0] if target_users else None
        
        task = TeamTask.objects.create(
            team=team,
            title=title,
            description=description,
            assigned_by=request.user,
            assigned_to=primary_assignee, # Legacy support
            due_date=due_date,
            status=status,
            column=col_todo  # Ensure it shows up on board
        )
        
        # Add all targets to ManyToMany field
        task.assignees.set(target_users)

        from .models import TeamTaskAttachment
        for att_data in attachments_data:
            TeamTaskAttachment.objects.create(
                task=task,
                file_name=att_data['name'],
                drive_file_id=att_data['file_id'],
                drive_link=att_data['drive_link'],
                uploaded_by=request.user
            )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Tasks created successfully'})
        
        # Redirect back to team tasks
        return redirect(f'/team/tasks/?team_id={team.id}')

    except Exception as e:
        print(f"Error creating team task: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def task_detail(request, task_id):
    """Detail view for a specific task"""
    task = get_object_or_404(TeamTask, id=task_id)
    # Check permissions (basic: user must be in the team)
    if not task.team.members.filter(id=request.user.id).exists():
         # Or handle via TeamMember check
         pass 

    comments = task.comments.all().select_related('author')
    history = task.history.all().select_related('user')
    # Prefetch attachments
    task_attachments = task.attachments.all()

    context = {
        'task': task,
        'team': task.team,
        'comments': comments,
        'history': history,
        'can_edit': task.assigned_by == request.user or request.user == task.team.creator # Simplified permission
    }
    return render(request, 'team_task_detail.html', context)

@login_required
@require_http_methods(["POST"])
def add_task_comment(request, task_id):
    """Add a comment to a task"""
    task = get_object_or_404(TeamTask, id=task_id)
    if not task.team.members.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    content = request.POST.get('content')
    if not content:
        return JsonResponse({'success': False, 'error': 'Content required'}, status=400)

    from .models import TeamTaskComment
    comment = TeamTaskComment.objects.create(
        task=task,
        author=request.user,
        content=content
    )

    # Log History
    TeamTaskHistory.objects.create(
        task=task,
        user=request.user,
        event_type='comment_added',
        new_value='Added a comment'
    )
    
    # If HTMX request, render the single comment
    # If HTMX request, render the single comment
    if request.headers.get('HX-Request') == 'true' or request.META.get('HTTP_HX_REQUEST') == 'true':
         return render(request, 'team/components/single_comment.html', {'comment': comment})

    return redirect('team:task_detail', task_id=task.id)

@login_required
@require_http_methods(["POST"])
def delete_section(request, column_id):
    """Delete a Kanban section"""
    column = get_object_or_404(TeamBoardColumn, id=column_id)
    team = column.team
    
    # Check permission
    if not TeamMember.objects.filter(team=team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Move tasks to fallback column if any
    fallback = TeamBoardColumn.objects.filter(team=team).exclude(id=column.id).order_by('order').first()
    if fallback:
        TeamTask.objects.filter(column=column).update(column=fallback)
        
    column.delete()
    return JsonResponse({'success': True, 'message': 'Section deleted'})

@login_required
@require_http_methods(["POST"])
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permission - assigned_by, or team admin/manager/owner can delete
    can_delete = (
        task.assigned_by == request.user or 
        TeamMember.objects.filter(team=task.team, user=request.user, role__in=['admin', 'manager', 'owner']).exists()
    )
    
    if not can_delete:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    task.delete()
    return JsonResponse({'success': True, 'message': 'Task deleted'})

@login_required
@require_http_methods(["POST"])
def delete_task_attachment(request, attachment_id):
    """Delete a task attachment"""
     # Handle circular import
    from .models import TeamTaskAttachment
    
    attachment = get_object_or_404(TeamTaskAttachment, id=attachment_id)
    
    # Check permission
    can_delete = (
        attachment.task.assigned_by == request.user or 
        TeamMember.objects.filter(team=attachment.task.team, user=request.user, role__in=['admin', 'manager', 'owner']).exists()
    )
    if not can_delete:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    attachment.delete()
    return JsonResponse({'success': True, 'message': 'Attachment deleted'})

@login_required
@require_http_methods(["POST"])
def edit_task(request, task_id):
    """Edit a team task"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permissions
    can_edit = (
        task.assigned_by == request.user or 
        TeamMember.objects.filter(team=task.team, user=request.user, role__in=['admin', 'manager', 'owner']).exists()
    )
    if not can_edit:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Update fields
    title = request.POST.get('name')
    if title:
        task.title = title
        
    priority = request.POST.get('priority')
    if priority:
        task.priority = priority
        
    due_date = request.POST.get('due_date')
    if due_date:
        task.due_date = due_date
    else:
        task.due_date = None

    description = request.POST.get('description')
    if description is not None:
        task.description = description
    
    # Store old assignees before updating
    old_assignees = set(task.assignees.all())
        
    task.save()
    
    # Handle assignee updates
    assign_to_team = request.POST.get('assign_to_team') == 'on'
    assigned_users_str = request.POST.get('assigned_users')
    
    # Only update assignees if one of the fields is present
    if assign_to_team or assigned_users_str is not None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        new_assignee_users = []

        if assign_to_team:
            # Assign to all team members
            team_member_ids = TeamMember.objects.filter(team=task.team).values_list('user_id', flat=True)
            new_assignee_users = User.objects.filter(id__in=team_member_ids)
        elif assigned_users_str:
            # Parse specific users
            user_ids = [int(x.strip()) for x in assigned_users_str.split(',') if x.strip().isdigit()]
            new_assignee_users = User.objects.filter(id__in=user_ids)
        
        # Set new assignees
        task.assignees.set(new_assignee_users)

        # Detect newly added assignees and send notifications
        new_assignees_set = set(new_assignee_users)
        added_assignees = new_assignees_set - old_assignees
        
        if added_assignees:
            from notifications.models import Notification
            for user in added_assignees:
                # Don't notify the user making the change
                if user.id != request.user.id and hasattr(user, 'member'):
                    Notification.create_notification(
                        recipient=user.member,
                        notification_type='task_assigned',
                        title=f'Task Assigned: {task.title}',
                        message=f'You have been assigned to "{task.title}" by {request.user.get_full_name() or request.user.username}',
                        link=f'/team/task/{task.id}/',
                        icon='fa-tasks',
                        content_object=task
                    )

    # Handle Attachments (Upload)
    if request.FILES.getlist('task_files'):
        from erp.google_drive import upload_file_to_drive
        from .models import TeamTaskAttachment
        
        for file_item in request.FILES.getlist('task_files'):
            upload_result = upload_file_to_drive(request.user, file_item, folder_name="ERP Team Tasks")
            
            if upload_result.get('success'):
                TeamTaskAttachment.objects.create(
                    task=task,
                    file_name=upload_result.get('name'),
                    drive_file_id=upload_result.get('file_id'),
                    drive_link=upload_result.get('drive_link'),
                    uploaded_by=request.user
                )
            else:
                print(f"Failed to upload attachment {file_item.name}: {upload_result.get('error')}")
    
    # Log history
    TeamTaskHistory.objects.create(
        task=task,
        user=request.user,
        event_type='status_change', # Using status_change as generic update for now or just log it
        new_value="Task details updated"
    )
    
    return JsonResponse({'success': True, 'message': 'Task updated successfully'})

@login_required
def team_messages(request):
    """Modern chat interface with rooms"""
    from .models import ChatRoom, ChatMessage
    
    user_teams = request.user.teams.all()
    team_id = request.GET.get('team_id')
    room_id = request.GET.get('room_id')
    
    if team_id:
        team = get_object_or_404(Team, id=team_id, members=request.user)
    else:
        team = get_user_team(request.user)
    
    # Get chat rooms for this team (only team's channels visible)
    channels = ChatRoom.objects.filter(team=team, room_type='channel').prefetch_related('members')
    direct_messages = ChatRoom.objects.filter(team=team, room_type='direct', members=request.user).prefetch_related('members')
    
    # Calculate unread counts
    for ch in channels:
        ch.unread = ch.get_unread_count(request.user)

    # Process DMs to have correct display name (Other User Name)
    for dm in direct_messages:
        dm.unread = dm.get_unread_count(request.user)
        other_member = dm.members.exclude(id=request.user.id).first()
        if other_member:
            dm.display_name = other_member.get_full_name()
        else:
            dm.display_name = dm.name

    # Get active room
    active_room = None
    messages = []
    if room_id:
        active_room = get_object_or_404(ChatRoom, id=room_id, team=team)
        # Set display name for active room if it's a DM
        if active_room.room_type == 'direct':
             other_member = active_room.members.exclude(id=request.user.id).first()
             if other_member:
                 active_room.display_name = other_member.get_full_name()
             else:
                 active_room.display_name = active_room.name
        else:
            active_room.display_name = active_room.name
            
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    elif channels.exists():
        active_room = channels.first()
        active_room.display_name = active_room.name
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    
    # Get team members for DM list (exclude current user and existing DMs)
    existing_dm_partner_ids = []
    for dm in direct_messages:
        for member in dm.members.all():
            if member.id != request.user.id:
                existing_dm_partner_ids.append(member.id)
                
    team_members = TeamMember.objects.filter(team=team).exclude(user=request.user).exclude(user__id__in=existing_dm_partner_ids).select_related('user')
    
    # Check Google Chat connection
    from authentication.models import GoogleChatCredentials
    is_google_connected = GoogleChatCredentials.objects.filter(user=request.user).exists()
    
    if active_room:
        messages = ChatMessage.objects.filter(room=active_room).order_by('created_at')

    # AJAX for room switching
    if request.GET.get('ajax') == '1':
        from django.template.loader import render_to_string
        html = render_to_string('team/partials/message_list.html', {'messages': messages, 'request': request})
        
        member_avatars = []
        for m in active_room.members.all()[:3]:
            member_avatars.append({
                'initials': (m.first_name[:1] + m.last_name[:1]).upper() if m.first_name and m.last_name else m.username[:2].upper(),
                'color_bg': '#dbeafe', # simplified for now, or cycle logic in JS? 
                'color_text': '#1a73e8'
            })
            
        return JsonResponse({
            'success': True,
            'room_id': active_room.id,
            'room_name': active_room.display_name,
            'description': active_room.description or "Team channel",
            'member_count': active_room.members.count(),
            'messages_html': html,
            'member_avatars': member_avatars
        })

    context = {
        'team': team,
        'user_teams': user_teams,
        'channels': channels,
        'direct_messages': direct_messages,
        'active_room': active_room,
        'messages': messages,
        'team_members': team_members,
        'is_google_connected': is_google_connected,
        'page_title': f'Messages - {team.name}',
    }
    return render(request, 'team_messages.html', context)

@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Send a message to team member"""
    try:
        data = json.loads(request.body)
        recipient_id = data.get('recipient_id')
        content = data.get('content')
        
        team = get_user_team(request.user)
        recipient = get_object_or_404(User, id=recipient_id)
        
        # Verify recipient is in team
        if not TeamMember.objects.filter(team=team, user=recipient).exists():
            return JsonResponse({'success': False, 'error': 'User not in team'}, status=403)
        
        message = TeamMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            team=team,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'sender': request.user.get_full_name(),
            'created_at': message.created_at.isoformat()
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

@login_required
def get_user_messages(request, user_id):
    """Get messages with specific user"""
    team = get_user_team(request.user)
    other_user = get_object_or_404(User, id=user_id)
    
    # Get conversation between request.user and other_user
    messages = TeamMessage.objects.filter(
        team=team
    ).filter(
        models.Q(sender=request.user, recipient=other_user) |
        models.Q(sender=other_user, recipient=request.user)
    ).select_related('sender', 'recipient').order_by('created_at')
    
    # Mark messages as read
    TeamMessage.objects.filter(recipient=request.user, sender=other_user, team=team, read_at__isnull=True).update(read_at=timezone.now())
    
    return JsonResponse({
        'success': True,
        'messages': [
            {
                'id': m.id,
                'sender_id': m.sender_id,
                'recipient_id': m.recipient_id,
                'sender_name': m.sender.get_full_name(),
                'content': m.content,
                'created_at': m.created_at.isoformat(),
                'is_sent': m.sender_id == request.user.id
            }
            for m in messages
        ]
    })

@login_required
def team_roles(request):
    """Manage team member roles"""
    team_id = request.GET.get('team_id')
    
    if team_id:
        team = get_object_or_404(Team, id=team_id, members=request.user)
    else:
        team = get_user_team(request.user)
    
    # Check if user is admin (allow access for testing, can add strict check later)
    try:
        user_role = TeamMember.objects.get(team=team, user=request.user)
    except TeamMember.DoesNotExist:
        return redirect('team:team_list')
    
    members = TeamMember.objects.filter(team=team).select_related('user')
    
    # Check if current user is the team creator
    is_creator = team.creator == request.user
    
    context = {
        'team': team,
        'members': members,
        'page_title': f'Manage Members - {team.name}',
        'role_choices': TeamMember.ROLE_CHOICES,
        'is_creator': is_creator,
    }
    return render(request, 'team_roles.html', context)

@login_required
@require_http_methods(["POST"])
def update_member_role(request, member_id):
    """Update team member role"""
    member = get_object_or_404(TeamMember, id=member_id)
    team = member.team
    
    # Only team creator can change roles
    if team.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Only team creator can change roles'}, status=403)
    
    new_role = request.POST.get('role')
    if new_role not in dict(TeamMember.ROLE_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid role'}, status=400)
    
    member.role = new_role
    member.save()
    
    return JsonResponse({'success': True, 'message': f'Role updated to {new_role}'})

@login_required
@require_http_methods(["POST"])
def remove_member(request, member_id):
    """Remove a member from the team"""
    member = get_object_or_404(TeamMember, id=member_id)
    team = member.team
    
    # Only team creator can remove members
    if team.creator != request.user:
        return JsonResponse({'success': False, 'error': 'Only team creator can remove members'}, status=403)
    
    # Cannot remove the team creator
    if member.user == team.creator:
        return JsonResponse({'success': False, 'error': 'Cannot remove the team creator'}, status=400)
    
    member_name = member.user.get_full_name() or member.user.username
    member.delete()
    
    return JsonResponse({'success': True, 'message': f'{member_name} has been removed from the team'})

@login_required
def team_meetings(request):
    """Display and schedule team meetings"""
    # Fetch all user's teams for the dropdown
    user_teams = request.user.teams.all()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        scheduled_at = request.POST.get('scheduled_at')
        duration_minutes = request.POST.get('duration_minutes', 60)
        meeting_link = request.POST.get('meeting_link', '')
        location = request.POST.get('location', '')
        create_meet = request.POST.get('create_meet') == 'on'
        participant_ids = request.POST.getlist('participants[]')
        
        # New: Determine Context
        meeting_type = request.POST.get('meeting_type', 'team') # 'team' or 'individual'
        team_id = request.POST.get('team_id')
        
        target_team = None
        if meeting_type == 'team' and team_id:
             target_team = get_object_or_404(Team, id=team_id)
             # Verify user membership
             if not target_team.members.filter(id=request.user.id).exists():
                 return HttpResponseForbidden("You are not a member of this team")
        
        # Create Google Meet if requested
        if create_meet:
            from erp.google_calendar import create_meet_event
            meet_result = create_meet_event(
                request.user, 
                title, 
                scheduled_at, 
                duration_minutes, 
                description
            )
            
            if meet_result.get('success'):
                meeting_link = meet_result.get('meet_link')
            else:
                 print(f"Failed to create Google Meet: {meet_result.get('error')}")

        meeting = TeamMeeting.objects.create(
            team=target_team, # Can be None now
            title=title,
            description=description,
            organizer=request.user,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            meeting_link=meeting_link,
            location=location
        )
        
        # Add participants
        if participant_ids:
            participants = User.objects.filter(id__in=participant_ids)
            meeting.participants.set(participants)
            users_to_notify = participants
        elif target_team:
            # If no specific participants selected for a team meeting, notify all team members
            users_to_notify = target_team.members.all()
        else:
             users_to_notify = []
        
        meeting.save()

        # Send Notifications
        from notifications.models import Notification
        from authentication.models import Member
        
        # Prepare notifications
        notifications_to_create = []
        
        # Get Members for users (efficiently)
        members_map = {m.user_id: m for m in Member.objects.filter(user__in=users_to_notify)}
        
        for user in users_to_notify:
            if user == request.user: continue # Don't notify organizer
            
            member = members_map.get(user.id)
            if member:
                 notifications_to_create.append(Notification(
                     recipient=member,
                     notification_type='meeting_invite',
                     title=f"New Meeting: {title}",
                     message=f"You have been invited to a meeting by {request.user.get_full_name()}.\nTime: {scheduled_at}",
                     link='/team/meetings/', # Or specific meeting detail if available
                     icon='fa-calendar-check',
                     content_object=meeting
                 ))
        
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Meeting scheduled successfully'})
        
        return redirect('team:team_meetings')
    
    from django.utils import timezone
    from django.db.models import Q
    now = timezone.now()
    
    # Fetch ALL relevant meetings (My Teams + Individual + Organized by me)
    # Distinct is important because user might be organizer AND participant AND team member
    base_query = TeamMeeting.objects.filter(
        Q(team__in=user_teams) | 
        Q(participants=request.user) | 
        Q(organizer=request.user)
    ).distinct()
    
    # Upcoming: Future meetings or today
    upcoming_meetings = base_query.filter(
        scheduled_at__gte=now
    ).order_by('scheduled_at').select_related('team', 'organizer').prefetch_related('participants')
    
    # History: Past meetings
    history_meetings = base_query.filter(
        scheduled_at__lt=now
    ).order_by('-scheduled_at').select_related('team', 'organizer').prefetch_related('participants')
    
    # Prepare teams data for frontend (ID, Name, Members)
    teams_data = []
    for t in user_teams:
        m_list = []
        for tm in t.member_objects.select_related('user').all():
             m_list.append({
                 'id': tm.user.id,
                 'name': tm.user.get_full_name() or tm.user.username,
                 'initials': (tm.user.first_name[:1] + tm.user.last_name[:1]) if tm.user.first_name and tm.user.last_name else tm.user.username[:2]
             })
        teams_data.append({
            'id': t.id,
            'name': t.name,
            'members': m_list
        })
    import json
    teams_json = json.dumps(teams_data)
    
    # Check if user has connected Google Account
    from authentication.models import GoogleChatCredentials
    is_google_connected = GoogleChatCredentials.objects.filter(user=request.user).exists()
    
    context = {
        'teams': user_teams,
        'teams_json': teams_json,
        'upcoming_meetings': upcoming_meetings,
        'history_meetings': history_meetings,
        'page_title': 'Team Meetings',
        'is_google_connected': is_google_connected,
    }
    return render(request, 'team_meetings.html', context)

@login_required
@require_http_methods(["POST"])
def create_meeting(request):
    """API endpoint to create meeting"""
    try:
        team = get_user_team(request.user)
        data = json.loads(request.body)
        
        meeting = TeamMeeting.objects.create(
            team=team,
            title=data.get('title'),
            description=data.get('description', ''),
            organizer=request.user,
            scheduled_at=data.get('scheduled_at'),
            duration_minutes=int(data.get('duration_minutes', 60)),
            meeting_link=data.get('meeting_link', ''),
            location=data.get('location', '')
        )
        
        participant_ids = data.get('participant_ids', [])
        if participant_ids:
            participants = User.objects.filter(id__in=participant_ids)
            meeting.participants.set(participants)
        
        return JsonResponse({'success': True, 'meeting_id': meeting.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def delete_meeting(request, meeting_id):
    """Delete a meeting"""
    meeting = get_object_or_404(TeamMeeting, id=meeting_id)
    
    # Check permission - only organizer can delete
    if meeting.organizer != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    meeting.delete()
    return JsonResponse({'success': True, 'message': 'Meeting deleted'})

@login_required
@require_http_methods(["POST"])
def create_instant_meeting(request):
    """Create an instant Google Meet and send it to the chat room"""
    import json
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        
        if not room_id:
             return JsonResponse({'success': False, 'error': 'Room ID required'}, status=400)

        # Get the room and team
        from .models import ChatRoom, ChatMessage
        room = get_object_or_404(ChatRoom, id=room_id)
        team = room.team
        
        # Check permissions
        # For channels: must be in team. For DMs: must be a member of the room
        if room.room_type == 'direct':
            if not room.members.filter(id=request.user.id).exists():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        else:
            if not team.members.filter(id=request.user.id).exists():
                 return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        # Initialize Google Calendar logic
        from erp.google_calendar import create_meet_event
        from django.utils import timezone
        
        now = timezone.now()
        # Round up to next 5 minutes for cleanliness, or just use now
        start_time = now.isoformat()
        
        title = f"Meeting in #{room.name}"
        if room.room_type == 'direct':
             title = f"Call with {request.user.first_name}"

        # Create Meet Event
        result = create_meet_event(
            user=request.user,
            title=title,
            start_time_iso=start_time,
            duration_minutes=30,
            description=f"Instant meeting started by {request.user.get_full_name()}"
        )
        
        if not result.get('success'):
             return JsonResponse({'success': False, 'error': result.get('error', 'Failed to create Meet')}, status=400)
             
        meet_link = result.get('meet_link')
        
        # Create a message with the link
        content = f"started a video call. <br> <a href='{meet_link}' target='_blank' class='btn btn-sm btn-primary mt-2'><i class='fas fa-video'></i> Join Meeting</a>"
        
        # Create ChatMessage (not TeamMessage)
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            content=content
        )

        # Sync with Google Chat if connected
        sync_status = 'skipped'
        if room.google_space_id:
            import threading
            def sync_to_google_chat(user_id, space_id, link, sender_name):
                try:
                    from authentication.models import GoogleChatCredentials
                    from google.oauth2.credentials import Credentials
                    from googleapiclient.discovery import build
                    from django.contrib.auth import get_user_model
                    
                    User = get_user_model()
                    user = User.objects.get(id=user_id)

                    creds_model = GoogleChatCredentials.objects.get(user=user)
                    creds = Credentials(
                        token=creds_model.token,
                        refresh_token=creds_model.refresh_token,
                        token_uri=creds_model.token_uri,
                        client_id=creds_model.client_id,
                        client_secret=creds_model.client_secret,
                        scopes=creds_model.scopes.split(' ') if creds_model.scopes else []
                    )
                    
                    service = build('chat', 'v1', credentials=creds)
                    
                    # Simple text message with link ensures visibility
                    text_message = {
                        'text': f"*{sender_name}* started a video call.\nJoin here: {link}"
                    }
                    
                    service.spaces().messages().create(
                        parent=space_id,
                        body=text_message
                    ).execute()
                    print(f"Async synced meeting to Google Chat Space: {space_id}")
                    
                except Exception as e:
                    print(f"Async logic failed to sync with Google Chat: {e}")

            # Start thread
            t = threading.Thread(target=sync_to_google_chat, args=(request.user.id, room.google_space_id, meet_link, request.user.get_full_name()))
            t.start()
            sync_status = 'async_started'
            
        else:
            print(f"Room {room.id} ({room.name}) has no google_space_id. Skipping sync.")
            sync_status = 'not_connected'

        return JsonResponse({
            'success': True,
            'meet_link': meet_link,
            'google_sync_status': sync_status,
            'message': {
                'id': message.id,
                'sender_initials': (request.user.first_name[:1] + request.user.last_name[:1]).upper() if request.user.first_name and request.user.last_name else request.user.username[:2].upper(),
                'sender_name': request.user.get_full_name(),
                'created_at': message.created_at.strftime('%H:%M'),
                'content': message.content,
                'is_own': True,
                'attachments': []
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def create_team(request):
    """Create a new team with optional members and roles"""
    try:
        # Support both form data and JSON
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description', '')
            members_data = data.get('members', [])  # [{user_id, role}, ...]
        else:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            members_data = []
            # Parse members from form data
            member_ids = request.POST.getlist('member_ids[]')
            member_roles = request.POST.getlist('member_roles[]')
            for i, uid in enumerate(member_ids):
                role = member_roles[i] if i < len(member_roles) else 'member'
                members_data.append({'user_id': int(uid), 'role': role})
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Team name is required'}, status=400)
        
        # Get icon_color from form or JSON
        icon_color = request.POST.get('icon_color', 'blue') if not request.content_type == 'application/json' else data.get('icon_color', 'blue')
        
        # Create team
        team = Team.objects.create(
            name=name,
            description=description,
            creator=request.user,
            icon_color=icon_color
        )
        
        # Add creator as admin
        TeamMember.objects.create(team=team, user=request.user, role='admin')
        
        # Create default chat room
        ChatRoom.objects.create(
            team=team,
            name='General',
            room_type='channel',
            created_by=request.user,
            is_default=True
        )
        
        # Send invitations to members
        from .models import TeamInvitation
        invited_count = 0
        
        for member_info in members_data:
            user_id = member_info.get('user_id')
            role = member_info.get('role', 'member')
            
            try:
                invited_user = User.objects.get(id=user_id)
                
                # Don't invite self
                if invited_user.id == request.user.id:
                    continue
                
                # Create invitation
                invitation = TeamInvitation.objects.create(
                    team=team,
                    invited_by=request.user,
                    invited_user=invited_user,
                    role=role,
                    message=f"You've been invited to join {team.name}"
                )
                
                # Create notification for the invited user
                try:
                    from authentication.models import Member
                    from notifications.models import Notification
                    
                    member = Member.objects.filter(user=invited_user).first()
                    if member:
                        Notification.create_notification(
                            recipient=member,
                            notification_type='team_invitation',
                            title=f"Team Invitation: {team.name}",
                            message=f"{request.user.get_full_name()} invited you to join {team.name} as {role.title()}",
                            link=f"/team/members/?invitation={invitation.token}",
                            icon='fa-users',
                            content_object=invitation
                        )
                except Exception as e:
                    print(f"Notification error: {e}")
                
                invited_count += 1
                
            except User.DoesNotExist:
                continue
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': f'Team created successfully. {invited_count} invitation(s) sent.',
                'team_id': team.id
            })
        
        return redirect('team:team_list')
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def search_users(request):
    """Search for users to add to team or assign tasks"""
    query = request.GET.get('q', '')
    team_id = request.GET.get('team_id')
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.all()
    
    # Filter by Team if provided (for task assignment)
    if team_id:
        try:
            team = Team.objects.get(id=team_id)
            # Ensure requester is member of team
            if not TeamMember.objects.filter(team=team, user=request.user).exists():
                return JsonResponse({'users': []}, status=403)
            
            # Filter users to only team members
            member_ids = TeamMember.objects.filter(team=team).values_list('user_id', flat=True)
            users = users.filter(id__in=member_ids)
        except (Team.DoesNotExist, ValueError):
            return JsonResponse({'users': []}, status=404)

    users = users.filter(
        models.Q(username__icontains=query) | 
        models.Q(first_name__icontains=query) | 
        models.Q(last_name__icontains=query) | 
        models.Q(email__icontains=query)
    )[:10]
    
    results = []
    for user in users:
        full_name = user.get_full_name() or user.username
        initials = ''
        if user.first_name and user.last_name:
            initials = user.first_name[0].upper() + user.last_name[0].upper()
        elif user.username:
            initials = user.username[:2].upper()
        
        results.append({
            'id': user.id,
            'name': full_name,
            'email': user.email or '',
            'initials': initials
        })
    
    return JsonResponse({'users': results})

@login_required
@login_required
@require_http_methods(["POST"])
def add_member(request):
    """Add a member to the team"""
    team_id = request.POST.get('team_id')
    if team_id:
        team = get_object_or_404(Team, id=team_id)
    else:
        team = get_user_team(request.user)
    
    # Check admin permission
    if not TeamMember.objects.filter(team=team, user=request.user, role__in=['admin', 'manager', 'owner']).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    role = request.POST.get('role', 'member')
    
    try:
        user = User.objects.get(id=user_id)
        
        if TeamMember.objects.filter(team=team, user=user).exists():
            return JsonResponse({'success': False, 'error': 'User already in team'}, status=400)
            
        TeamMember.objects.create(team=team, user=user, role=role)
        
        return JsonResponse({'success': True, 'message': 'Member added successfully'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)


@login_required
def pending_invitations(request):
    """Get pending invitations for current user"""
    from .models import TeamInvitation
    
    invitations = TeamInvitation.objects.filter(
        invited_user=request.user,
        status='pending'
    ).select_related('team', 'invited_by')
    
    data = [{
        'id': inv.id,
        'token': inv.token,
        'team_name': inv.team.name,
        'team_id': inv.team.id,
        'invited_by': inv.invited_by.get_full_name(),
        'role': inv.role,
        'role_display': inv.get_role_display(),
        'message': inv.message,
        'created_at': inv.created_at.isoformat(),
        'expires_at': inv.expires_at.isoformat() if inv.expires_at else None,
        'is_expired': inv.is_expired()
    } for inv in invitations]
    
    return JsonResponse({'success': True, 'invitations': data, 'count': len(data)})


@login_required
@require_http_methods(["POST"])
def respond_invitation(request, token):
    """Accept or decline an invitation"""
    from .models import TeamInvitation
    
    try:
        invitation = TeamInvitation.objects.get(
            token=token,
            invited_user=request.user,
            status='pending'
        )
    except TeamInvitation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invitation not found or already processed'}, status=404)
    
    action = request.POST.get('action', 'accept')
    
    if action == 'accept':
        if invitation.accept():
            return JsonResponse({
                'success': True, 
                'message': f'You have joined {invitation.team.name}!',
                'team_id': invitation.team.id
            })
        else:
            return JsonResponse({'success': False, 'error': 'Could not accept invitation'}, status=400)
    
    elif action == 'decline':
        if invitation.decline():
            return JsonResponse({'success': True, 'message': 'Invitation declined'})
        else:
            return JsonResponse({'success': False, 'error': 'Could not decline invitation'}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)


@login_required
def get_team_invitations(request, team_id):
    """Get all invitations for a team (admin only)"""
    from .models import TeamInvitation
    
    team = get_object_or_404(Team, id=team_id)
    
    # Check if user is admin
    if not TeamMember.objects.filter(team=team, user=request.user, role='admin').exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    invitations = TeamInvitation.objects.filter(team=team).select_related('invited_user', 'invited_by')
    
    data = [{
        'id': inv.id,
        'invited_user': inv.invited_user.get_full_name(),
        'invited_user_email': inv.invited_user.email,
        'invited_by': inv.invited_by.get_full_name(),
        'role': inv.role,
        'status': inv.status,
        'created_at': inv.created_at.isoformat(),
    } for inv in invitations]
    
    return JsonResponse({'success': True, 'invitations': data})


@login_required
@require_http_methods(["POST"])
def create_chat_room(request):
    """Create a new chat room/channel"""
    from .models import ChatRoom
    
    team_id = request.POST.get('team_id')
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    room_type = request.POST.get('room_type', 'channel')
    user_id = request.POST.get('user_id')  # For direct messages
    
    if not team_id:
        return JsonResponse({'success': False, 'error': 'Team required'}, status=400)
    
    team = get_object_or_404(Team, id=team_id, members=request.user)
    
    # Handle direct message
    if room_type == 'direct' and user_id:
        target_user = get_object_or_404(User, id=user_id)
        
        # Check if DM already exists between these users
        existing_room = ChatRoom.objects.filter(
            team=team,
            room_type='direct',
            members=request.user
        ).filter(members=target_user).first()
        
        if existing_room:
            return JsonResponse({'success': True, 'room_id': existing_room.id, 'message': 'Existing conversation'})
        
        # Create new DM room
        room = ChatRoom.objects.create(
            team=team,
            name=f"DM: {request.user.get_full_name()} & {target_user.get_full_name()}",
            room_type='direct',
            created_by=request.user
        )
        room.members.add(request.user, target_user)
        
        # Try to find/link Google Chat DM
        try:
            service = get_google_chat_service(request.user)
            if service:
                # Check if target has Google Creds
                creds = GoogleChatCredentials.objects.filter(user=target_user).first()
                target_email = creds.email if creds and creds.email else target_user.email
                
                if target_email:
                    try:
                        dm_space = service.spaces().findDirectMessage(name=f"users/{target_email}").execute()
                        room.google_space_id = dm_space['name']
                        room.save()
                    except Exception as e:
                        print(f"DM Lookup Error: {e}")
                        google_error = str(e)
        except Exception as e:
            # Suppress 404 Not Found for DMs to avoid user alert
            if '404' not in str(e):
                print(f"Google Chat DM Error: {e}")
                google_error = str(e)
            else:
                print(f"Google Chat DM not found (ignored): {e}")

        response_data = {'success': True, 'room_id': room.id, 'message': 'Conversation started'}
        if 'google_error' in locals():
            response_data['warning'] = f"Conversation started but Google Chat sync failed: {google_error}"

        return JsonResponse(response_data)
    
    # Handle channel creation
    if not name:
        return JsonResponse({'success': False, 'error': 'Name required'}, status=400)
    
    room = ChatRoom.objects.create(
        team=team,
        name=name,
        description=description,
        room_type=room_type,
        created_by=request.user
    )

    # Try to create Google Chat Space
    try:
        service = get_google_chat_service(request.user)
        if service:
            space = service.spaces().create(
                body={'displayName': name, 'spaceType': 'SPACE'}
            ).execute()
            room.google_space_id = space['name']
            room.save()
    except Exception as e:
        print(f"Failed to create Google Space: {e}")
        google_error = str(e)
    
    # Add all team members to the channel
    for member in team.members.all():
        room.members.add(member)
    
    response_data = {'success': True, 'room_id': room.id, 'message': 'Channel created'}
    if 'google_error' in locals():
        response_data['warning'] = f"Channel created but Google Chat sync failed: {google_error}"
        
    return JsonResponse(response_data)


@login_required
def get_chat_updates(request):
    """Poll for new messages and typing status"""
    from .models import ChatMessage, ChatTypingStatus, ChatRoom
    from django.utils import timezone
    from datetime import timedelta
        
    room_id = request.GET.get('room_id')
    last_message_id = request.GET.get('last_message_id', 0)
    
    data = {'messages': [], 'typing': []}
    
    if room_id:
        # Get new messages
        new_messages = ChatMessage.objects.filter(
            room_id=room_id, 
            id__gt=last_message_id
        ).select_related('sender').prefetch_related('attachments').order_by('created_at')
        
        for msg in new_messages:
            attachments = [{
                'id': f.id,
                'name': f.file_name,
                'url': f.file.url if f.file else '',
                'type': f.file_type,
                'size': f.file_size
            } for f in msg.attachments.all()]
            
            data['messages'].append({
                'id': msg.id,
                'content': msg.content,
                'sender_id': msg.sender.id,
                'sender_name': msg.sender.get_full_name(),
                'sender_initials': f"{msg.sender.first_name[:1]}{msg.sender.last_name[:1]}".upper(),
                'created_at': msg.created_at.strftime('%I:%M %p'),
                'is_own': msg.sender.id == request.user.id,
                'attachments': attachments
            })
            
        # Get typing status (active in last 5 seconds)
        threshold = timezone.now() - timedelta(seconds=5)
        typing_users = ChatTypingStatus.objects.filter(
            room_id=room_id,
            last_typed__gte=threshold
        ).exclude(user=request.user).select_related('user')
        
        data['typing'] = [u.user.get_full_name() for u in typing_users]

        # Update Read Marker for current room
        from .models import ChatReadMarker
        ChatReadMarker.objects.update_or_create(
            room_id=room_id,
            user=request.user,
            defaults={'last_read_at': timezone.now()}
        )

    # Get unread counts for ALL user's rooms
    user_rooms = ChatRoom.objects.filter(members=request.user)
    unread_counts = {}
    for room in user_rooms:
        count = room.get_unread_count(request.user)
        if count > 0:
            unread_counts[room.id] = count
            
    data['unread_counts'] = unread_counts

    return JsonResponse(data)

@login_required
@require_http_methods(["POST"])
def update_typing_status(request):
    """Update user's typing timestamp"""
    from .models import ChatTypingStatus
    room_id = request.POST.get('room_id')
    if room_id:
        ChatTypingStatus.objects.update_or_create(
            room_id=room_id,
            user=request.user,
            defaults={'last_typed': timezone.now()}
        )
    return JsonResponse({'success': True})

@login_required
@require_http_methods(["POST"])
def upload_chat_file(request):
    """Handle file upload via AJAX"""
    from .models import ChatFile, ChatRoom
    
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
    file_obj = request.FILES['file']
    room_id = request.POST.get('room_id')
    
    if not room_id:
        return JsonResponse({'success': False, 'error': 'Room ID required'}, status=400)
        
    # Determine file type
    content_type = file_obj.content_type
    file_type = 'other'
    if content_type.startswith('image/'): file_type = 'image'
    elif content_type.startswith('video/'): file_type = 'video'
    elif content_type.startswith('audio/'): file_type = 'audio'
    elif 'pdf' in content_type or 'word' in content_type or 'text' in content_type: file_type = 'document'
    
    chat_file = ChatFile.objects.create(
        room_id=room_id,
        uploader=request.user,
        file=file_obj,
        file_name=file_obj.name,
        file_type=file_type,
        file_size=file_obj.size
    )
    
    return JsonResponse({
        'success': True,
        'file_id': chat_file.id,
        'file_name': chat_file.file_name,
        'file_url': chat_file.file.url
    })

@login_required
@require_http_methods(["POST"])
@transaction.atomic
def send_chat_message(request):
    """Send a message to a chat room"""
    from .models import ChatRoom, ChatMessage, ChatFile
    from django.db import transaction
    
    data = json.loads(request.body)
    room_id = data.get('room_id')
    content = data.get('content', '')
    attachment_ids = data.get('attachments', [])
    
    if not room_id or (not content and not attachment_ids):
        return JsonResponse({'success': False, 'error': 'Room and content/attachment required'}, status=400)
    
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check if user is team member
    if not TeamMember.objects.filter(team=room.team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    message = ChatMessage.objects.create(
        room=room,
        sender=request.user,
        content=content
    )
    
    # Link attachments
    if attachment_ids:
        ChatFile.objects.filter(id__in=attachment_ids, uploader=request.user).update(message=message)
    
    # Sync to Google Chat
    try:
        service = get_google_chat_service(request.user)
        if service:
            space_name = room.google_space_id
            
            # If DM and no space yet, try to find it
            if not space_name and room.room_type == 'direct':
                other_member = room.members.exclude(id=request.user.id).first()
                if other_member:
                    creds = GoogleChatCredentials.objects.filter(user=other_member).first()
                    # STRICT CHECK: Only sync if recipient has integrated Google Chat
                    if creds and creds.email:
                        target_email = creds.email
                        try:
                            # Try to find DM space
                            dm_space = service.spaces().findDirectMessage(name=f"users/{target_email}").execute()
                            space_name = dm_space['name']
                            room.google_space_id = space_name
                            room.save()
                        except Exception as e:
                            # Silent fail for lookup
                            print(f"Could not find DM space for {target_email}: {e}")
                    else:
                        space_name = None

            if space_name:
                service.spaces().messages().create(
                    parent=space_name,
                    body={'text': content}
                ).execute()
    except Exception as e:
        print(f"Google Chat Sync Error: {e}")

    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'sender_id': message.sender.id,
            'sender_name': message.sender.get_full_name(),
            'sender_initials': f"{message.sender.first_name[:1]}{message.sender.last_name[:1]}".upper(),
            'created_at': message.created_at.strftime('%I:%M %p'),
            'attachments': [{'url': f.file.url, 'name': f.file_name, 'type': f.file_type} for f in message.attachments.all()]
        }
    })


@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, team_id):
    """Toggle favorite status for a team"""
    team = get_object_or_404(Team, id=team_id)
    
    # Check if user is member
    if not TeamMember.objects.filter(team=team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    fav, created = FavoriteTeam.objects.get_or_create(user=request.user, team=team)
    if not created:
        fav.delete()
        is_favorite = False
    else:
        is_favorite = True
    
    return JsonResponse({'success': True, 'is_favorite': is_favorite})

@login_required
@require_http_methods(["POST"])
def archive_team(request, team_id):
    """Archive a team"""
    team = get_object_or_404(Team, id=team_id)
    
    # Only creator (and maybe admin) can archive
    # Checking if user is the creator or has admin role in team
    is_admin = TeamMember.objects.filter(team=team, user=request.user, role='admin').exists()
    
    if team.creator != request.user and not is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    team.is_archived = True
    team.save()
    
    return JsonResponse({'success': True, 'message': 'Team archived'})

@login_required
def get_manageable_teams(request):
    """Get teams where user has admin/manager/owner role for task assignment"""
    manageable_memberships = TeamMember.objects.filter(
        user=request.user,
        role__in=['admin', 'manager', 'owner']
    ).select_related('team').filter(team__is_archived=False)
    
    teams = [{'id': m.team.id, 'name': m.team.name} for m in manageable_memberships]
    return JsonResponse({'teams': teams})

# ------------------- Google Chat Integration -------------------

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from authentication.models import GoogleChatCredentials

def get_google_chat_service(user):
    """Build and return a Google Chat API service for the user"""
    try:
        creds_model = GoogleChatCredentials.objects.get(user=user)
        
        credentials = Credentials(
            token=creds_model.token,
            refresh_token=creds_model.refresh_token,
            token_uri=creds_model.token_uri,
            client_id=creds_model.client_id,
            client_secret=creds_model.client_secret,
            scopes=creds_model.scopes.split(' ')
        )
        
        return build('chat', 'v1', credentials=credentials)
    except GoogleChatCredentials.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error building chat service: {e}")
        return None

@login_required
def get_google_spaces(request):
    """Fetch list of spaces (DMs and Rooms) from Google Chat"""
    service = get_google_chat_service(request.user)
    if not service:
        # 401 Unauthorized for not connected state, but for AJAX usage 200 with success:false is often easier to handle
        return JsonResponse({'success': False, 'error': 'Not connected to Google Chat'})
    
    try:
        # Fetch spaces (both DMs and Rooms)
        results = service.spaces().list().execute()
        spaces = results.get('spaces', [])
        
        formatted_spaces = []
        for space in spaces:
             # Determine name (DM doesn't always have displayName)
            name = space.get('displayName')
            if not name and space.get('type') == 'DM':
                name = "Direct Message" 
            
            formatted_spaces.append({
                'id': space['name'], # spaces/AAAAAAAA
                'name': name or "Unnamed Space",
                'type': space.get('type'),
                'unread': 0
            })
            
        return JsonResponse({'success': True, 'spaces': formatted_spaces})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_google_messages(request):
    """Fetch messages for a specific space"""
    space_name = request.GET.get('space_name') # spaces/XYZ
    if not space_name:
         return JsonResponse({'success': False, 'error': 'Space name required'})

    service = get_google_chat_service(request.user)
    if not service:
        return JsonResponse({'success': False, 'error': 'Not connected'})
        
    try:
        # Fetch messages
        results = service.spaces().messages().list(
            parent=space_name,
            orderBy='createTime desc', 
            pageSize=50
        ).execute()
        
        raw_messages = results.get('messages', [])
        messages = []
        
        for msg in reversed(raw_messages): # Reverse to show oldest to newest
            sender = msg.get('sender', {})
            
            messages.append({
                'id': msg['name'],
                'content': msg.get('text', ''),
                'sender': sender.get('displayName', 'Unknown'),
                'sender_avatar': sender.get('avatarUrl', ''),
                'created_at': msg.get('createTime'),
            })
            
        return JsonResponse({'success': True, 'messages': messages})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def send_google_message(request):
    """Send a message to a Google Chat space"""
    try:
        data = json.loads(request.body)
        space_name = data.get('space_name')
        content = data.get('content')
        
        if not space_name or not content:
             return JsonResponse({'success': False, 'error': 'Missing data'})

        service = get_google_chat_service(request.user)
        if not service:
             return JsonResponse({'success': False, 'error': 'Not connected'})
             
        # Send message
        result = service.spaces().messages().create(
            parent=space_name,
            body={'text': content}
        ).execute()
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': result['name'],
                'content': result.get('text', ''),
                'sender': result.get('sender', {}).get('displayName', ''),
                'created_at': result.get('createTime')
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_team_task_edit_form(request, task_id):
    """Get the team task edit form partial for sidebar"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permissions and get role
    try:
        member = TeamMember.objects.get(team=task.team, user=request.user)
    except TeamMember.DoesNotExist:
        return HttpResponseForbidden("Permission denied")

    # Determine edit permission
    # Editable if:
    # 1. User is the creator/assigner of the task
    # 2. User is an Admin or Manager of the team
    is_assigner = task.assigned_by == request.user
    is_admin_or_manager = member.role in ['admin', 'manager']
    
    can_edit = is_assigner or is_admin_or_manager

    # Render template
    html = render_to_string('team/components/task_edit_form.html', {
        'task': task,
        'team': task.team,
        'can_edit': can_edit,
    }, request=request)
    
    return HttpResponse(html)
