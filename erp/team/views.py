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

from .models import Team, TeamMember, TeamMessage, TeamMeeting, FavoriteTeam, ChatRoom, TeamBoardColumn
from todo.models import Task, TaskActivity, TaskAttachment, TaskComment
from todo.repeat import from_form as repeat_from_form
from .access import has_team_role, is_team_member, team_role, teams_for

def get_user_team(user):
    """Get the user's primary team (first team they belong to or created)"""
    # An admin in no team opens one of everybody's rather than being
    # given a new team of their own.
    team = user.teams.first() or teams_for(user).filter(is_archived=False).first()
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
    """Team Overview - Display all user's teams with cards.
    All teams (active + archived) are rendered; tab switching is client-side."""
    filter_type = request.GET.get('filter', 'all')

    teams = teams_for(request.user).prefetch_related('member_objects__user', 'tasks')
    favorite_ids = set(FavoriteTeam.objects.filter(user=request.user).values_list('team_id', flat=True))
    for t in teams:
        t.is_favorite = t.id in favorite_ids

    active_count = sum(1 for t in teams if not t.is_archived)
    favorite_count = sum(1 for t in teams if t.is_favorite and not t.is_archived)
    archived_count = sum(1 for t in teams if t.is_archived)

    context = {
        'teams': teams,
        'filter': filter_type,
        'all_count': active_count,
        'favorite_count': favorite_count,
        'archived_count': archived_count,
        'page_title': 'Team Overview',
    }
    return render(request, 'team_list.html', context)

def _member(user):
    """The Member behind a login, or None."""
    return getattr(user, 'member', None)


def _members_of(users):
    """The Members behind these logins — a team task's people are members."""
    from authentication.models import Member
    return list(Member.objects.filter(user__in=list(users)))


def _team_task(task_id):
    """A team task by id: a Task that belongs to a team."""
    return get_object_or_404(Task.objects.exclude(team=None), id=task_id)


def _is_creator(task, user):
    member = _member(user)
    return bool(member and task.created_by_id == member.id)


def _log(task, user, activity_type, new_value, old_value=None):
    TaskActivity.objects.create(
        task=task, user=_member(user), activity_type=activity_type,
        old_value=old_value, new_value=new_value)


def _parse_due(value):
    """A posted due date, as a date; None when blank or unreadable."""
    from datetime import date
    try:
        return date.fromisoformat((value or '').strip()[:10])
    except ValueError:
        return None


def _target_users(request, team):
    """Who a new or edited team task goes to, from the posted form:
    the whole team, the listed users, the one legacy user, or (for a new
    task) nobody — the caller falls back to the author."""
    if request.POST.get('assign_to_team') == 'on':
        return [tm.user for tm in TeamMember.objects.filter(team=team).select_related('user')]
    assigned_users_str = request.POST.get('assigned_users', '')
    if assigned_users_str:
        user_ids = [int(x) for x in assigned_users_str.split(',') if x.strip().isdigit()]
        return list(User.objects.filter(id__in=user_ids))
    if request.POST.get('assigned_to'):
        return list(User.objects.filter(id=request.POST.get('assigned_to')))
    return []


def _attach_uploads(request, task):
    """Upload the posted files to Drive and attach them to the task."""
    files = request.FILES.getlist('task_files')
    if not files:
        return
    from erp.google_drive import upload_file_to_drive
    uploader = _member(request.user)
    if uploader is None:
        return
    for file_item in files:
        result = upload_file_to_drive(request.user, file_item, folder_name="ERP Team Tasks")
        if result.get('success'):
            TaskAttachment.objects.create(
                task=task,
                file_name=result.get('name'),
                drive_file_id=result.get('file_id'),
                drive_link=result.get('drive_link'),
                uploaded_by=uploader,
            )
        else:
            print(f"Failed to upload attachment {file_item.name}: {result.get('error')}")


def _notify_assigned(request, task, users, title_prefix):
    """Tell each newly assigned person, except the one assigning. The
    task's own member is told by the Task signal when it is created."""
    from notifications.models import Notification
    for user in users:
        member = _member(user)
        if member is None or user.id == request.user.id:
            continue
        Notification.create_notification(
            recipient=member,
            notification_type='task_assigned',
            title=f'{title_prefix}: {task.name}',
            message=f'You have been assigned to "{task.name}" by {request.user.get_full_name() or request.user.username}',
            link=task.get_absolute_url(),
            icon='fa-tasks',
            content_object=task,
        )


def _create_team_task(request, team):
    """Create a team task from the posted form; returns it."""
    name = request.POST.get('name') or request.POST.get('title')
    target_users = _target_users(request, team) or [request.user]

    col_todo = TeamBoardColumn.objects.filter(team=team, title='To Do').first()
    if not col_todo:
        col_todo = TeamBoardColumn.objects.create(team=team, title='To Do', color='blue', order=0)

    task = Task(
        team=team,
        column=col_todo,
        name=name,
        description=request.POST.get('description', ''),
        due_date=_parse_due(request.POST.get('due_date')) or timezone.localdate(),
        priority=request.POST.get('priority', 'medium'),
        created_by=_member(request.user),
        member=_member(target_users[0]),
    )
    task.set_repeat(*repeat_from_form(request.POST))
    task.set_status(request.POST.get('status', 'todo'))
    task.save()
    task.assignees.set(_members_of(target_users))
    _log(task, request.user, 'created', name)

    primary = task.member.user_id if task.member else None
    _notify_assigned(request, task, [u for u in target_users if u.id != primary], 'New Task')

    try:
        from todo.google_tasks import push_task_to_google
        push_task_to_google(request.user, task)
    except Exception as e:
        print(f"Error pushing team task to Google Tasks: {e}")

    _attach_uploads(request, task)
    return task


@login_required
def team_tasks(request):
    """Kanban task board with columns"""
    team_id = request.GET.get('team_id')
    if team_id:
        team = get_object_or_404(teams_for(request.user), id=team_id)
    else:
        team = get_user_team(request.user)

    if request.method == 'POST':
        try:
            if not (request.POST.get('title') or request.POST.get('name')):
                return JsonResponse({'success': False, 'error': 'Task name is required'})
            form_team_id = request.POST.get('team_id')
            if form_team_id:
                team = get_object_or_404(Team, id=form_team_id)
            _create_team_task(request, team)
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

    columns = list(columns)

    # A task with no column (its column was deleted, say) goes back to
    # the column named for its status, so nothing falls off the board.
    col_map = {c.title: c for c in columns}
    status_map = {'todo': 'To Do', 'in_progress': 'In Progress', 'review': 'Review', 'done': 'Done'}
    for status_code, col_title in status_map.items():
        if col_title in col_map:
            Task.objects.filter(team=team, column__isnull=True, status=status_code).update(
                column=col_map[col_title])

    all_tasks = (Task.objects.filter(team=team)
                 .select_related('member__user', 'created_by__user', 'column')
                 .prefetch_related('assignees__user', 'attachments'))

    for col in columns:
        col.task_list = [t for t in all_tasks if t.column_id == col.id]

    user_role = team_role(request.user, team) or 'member'

    context = {
        'team': team,
        'user_teams': teams_for(request.user).filter(is_archived=False),
        'members': TeamMember.objects.filter(team=team).select_related('user'),
        'columns': columns,
        'page_title': f'{team.name} Tasks',
        'user_role': user_role,
    }
    return render(request, 'team_tasks.html', context)

@login_required
@require_http_methods(["POST"])
def complete_task(request, task_id):
    """Mark task as completed"""
    task = _team_task(task_id)
    member = _member(request.user)

    is_assignee = bool(member and task.member_id == member.id)
    if not (is_assignee or _is_creator(task, request.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    task.set_status('done')
    task.save()

    return JsonResponse({'success': True, 'message': 'Task marked as completed'})

@login_required
@require_http_methods(["POST"])
def update_task_status(request, task_id):
    """Update task status (for Kanban drag-and-drop)"""
    task = _team_task(task_id)

    # Allowed: assignees, the creator, or the team's admins and managers
    member = _member(request.user)
    is_assignee = bool(member and task.assignees.filter(id=member.id).exists())
    is_admin = has_team_role(request.user, task.team)

    if not (is_assignee or _is_creator(task, request.user) or is_admin):
        return JsonResponse({'success': False, 'error': 'You can only move your own tasks'}, status=403)

    new_status = request.POST.get('status')
    column_id = request.POST.get('column_id')

    if column_id:
        column = get_object_or_404(TeamBoardColumn, id=column_id, team=task.team)
        task.column = column
        task.set_status('done' if column.title.lower() == 'done' else 'todo')
        task.save()

        _log(task, request.user, 'status_changed', column.title, old_value='(Drag & Drop)')

        try:
            from todo.google_tasks import update_task_in_google
            update_task_in_google(request.user, task)
        except Exception as e:
            print(f"Error updating team task in Google Tasks: {e}")

        return JsonResponse({'success': True, 'message': f'Task moved to {column.title}'})

    # Legacy status update support (drag drop via data-status)
    valid_statuses = ['todo', 'in_progress', 'review', 'done']

    if new_status and new_status in valid_statuses:
        title_map = {'todo': 'To Do', 'in_progress': 'In Progress', 'review': 'Review', 'done': 'Done'}
        col = TeamBoardColumn.objects.filter(team=task.team, title=title_map[new_status]).first()
        if col:
            task.column = col
        task.set_status(new_status)
        task.save()

        _log(task, request.user, 'status_changed', new_status)

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
    if not is_team_member(request.user, team):
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
    if not is_team_member(request.user, column.team):
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
    if not (request.POST.get('title') or request.POST.get('name')):
        return JsonResponse({'success': False, 'error': 'Task name is required'})

    try:
        form_team_id = request.POST.get('team_id')
        if form_team_id:
            team = get_object_or_404(Team, id=form_team_id)
        else:
            team = get_user_team(request.user)

        _create_team_task(request, team)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Tasks created successfully'})

        return redirect(f'/team/tasks/?team_id={team.id}')

    except Exception as e:
        print(f"Error creating team task: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def task_detail(request, task_id):
    """Detail view for a specific task"""
    task = get_object_or_404(
        Task.objects.exclude(team=None).select_related(
            'team', 'column', 'member__user', 'created_by__user'
        ).prefetch_related(
            'assignees__user', 'team__columns'
        ),
        id=task_id
    )

    comments = task.comments.all().select_related('author__user')
    history = task.activities.all().select_related('user__user')

    context = {
        'task': task,
        'team': task.team,
        'comments': comments,
        'history': history,
        'can_edit': _is_creator(task, request.user) or request.user == task.team.creator or has_team_role(request.user, task.team, ('admin',))
    }
    return render(request, 'team_task_detail.html', context)

@login_required
@require_http_methods(["POST"])
def add_task_comment(request, task_id):
    """Add a comment to a task"""
    task = _team_task(task_id)
    if not is_team_member(request.user, task.team):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    content = request.POST.get('content')
    if not content:
        return JsonResponse({'success': False, 'error': 'Content required'}, status=400)

    author = _member(request.user)
    if author is None:
        return JsonResponse({'success': False, 'error': 'Only members can comment'}, status=403)

    comment = TaskComment.objects.create(task=task, author=author, content=content)

    _log(task, request.user, 'comment_added', 'Added a comment')

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
    if not is_team_member(request.user, team):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    # Move tasks to fallback column if any
    fallback = TeamBoardColumn.objects.filter(team=team).exclude(id=column.id).order_by('order').first()
    if fallback:
        Task.objects.filter(column=column).update(column=fallback)

    column.delete()
    return JsonResponse({'success': True, 'message': 'Section deleted'})

@login_required
@require_http_methods(["POST"])
def delete_task(request, task_id):
    """Delete a task"""
    task = _team_task(task_id)

    # The creator, or the team's admins and managers
    if not (_is_creator(task, request.user) or has_team_role(request.user, task.team)):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    task.delete_from_series(keep_series=request.POST.get('keep_series') == '1')
    return JsonResponse({'success': True, 'message': 'Task deleted'})

@login_required
@require_http_methods(["POST"])
def delete_task_attachment(request, attachment_id):
    """Delete a task attachment"""
    attachment = get_object_or_404(TaskAttachment.objects.exclude(task__team=None), id=attachment_id)
    task = attachment.task

    if not (_is_creator(task, request.user) or has_team_role(request.user, task.team)):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    attachment.delete()
    return JsonResponse({'success': True, 'message': 'Attachment deleted'})

@login_required
@require_http_methods(["POST"])
def edit_task(request, task_id):
    """Edit a team task"""
    task = _team_task(task_id)

    if not (_is_creator(task, request.user) or has_team_role(request.user, task.team)):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    before = (task.name, task.description, task.priority, task.due_date)

    name = request.POST.get('name')
    if name:
        task.name = name

    priority = request.POST.get('priority')
    if priority:
        task.priority = priority

    # A task always has a due date; a blank field leaves it as it was.
    due_date = _parse_due(request.POST.get('due_date'))
    if due_date:
        task.set_due_date(due_date)

    if 'repeat_unit' in request.POST:
        task.set_repeat(*repeat_from_form(request.POST))

    description = request.POST.get('description')
    if description is not None:
        task.description = description

    old_assignees = set(task.assignees.all())

    task.save()

    # Only update assignees if one of the fields is present
    if request.POST.get('assign_to_team') == 'on' or request.POST.get('assigned_users') is not None:
        new_users = _target_users(request, task.team)
        new_members = _members_of(new_users)
        task.assignees.set(new_members)
        added = {m.user_id for m in set(new_members) - old_assignees}
        _notify_assigned(request, task, [u for u in new_users if u.id in added], 'Task Assigned')

    _attach_uploads(request, task)

    # What changed, the way a personal task's edit records it.
    old_name, old_description, old_priority, old_due = before
    if task.name != old_name:
        _log(task, request.user, 'name_updated', task.name, old_value=old_name)
    if (task.description or '') != (old_description or ''):
        _log(task, request.user, 'description_updated', (task.description or '')[:100] or None,
             old_value=(old_description or '')[:100] or None)
    if task.priority != old_priority:
        _log(task, request.user, 'priority_changed', task.priority, old_value=old_priority)
    if task.due_date != old_due:
        _log(task, request.user, 'due_date_changed', task.due_date.isoformat(),
             old_value=old_due.isoformat() if old_due else None)

    try:
        from todo.google_tasks import update_task_in_google
        update_task_in_google(request.user, task)
    except Exception as e:
        print(f"Error updating team task in Google Tasks: {e}")

    return JsonResponse({'success': True, 'message': 'Task updated successfully'})

@login_required
def team_messages(request):
    """Modern chat interface with rooms"""
    from .models import ChatRoom, ChatMessage
    
    user_teams = teams_for(request.user)
    team_id = request.GET.get('team_id')
    room_id = request.GET.get('room_id')
    
    if team_id:
        team = get_object_or_404(teams_for(request.user), id=team_id)
    else:
        team = get_user_team(request.user)
    
    # -------------------------------------------------------------------------
    # AJAX FAST-PATH FOR ROOM SWITCHING
    # Return messages HTML instantly without fetching the rest of the sidebar
    # -------------------------------------------------------------------------
    if request.GET.get('ajax') == '1':
        if not room_id:
            return JsonResponse({'success': False, 'error': 'Room ID missing'})
            
        active_room = get_object_or_404(ChatRoom, id=room_id, team=team)
        if active_room.room_type == 'direct':
             other_member = active_room.members.exclude(id=request.user.id).first()
             active_room.display_name = other_member.get_full_name() if other_member else active_room.name
        else:
             active_room.display_name = active_room.name
             
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
        
        from django.template.loader import render_to_string
        html = render_to_string('team/partials/message_list.html', {'messages': messages, 'request': request})
        
        member_avatars = []
        for m in active_room.members.all()[:3]:
            member_avatars.append({
                'initials': (m.first_name[:1] + m.last_name[:1]).upper() if m.first_name and m.last_name else m.username[:2].upper(),
                'color_bg': '#dbeafe', 
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
    # -------------------------------------------------------------------------

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

    # Get active room for full page load
    active_room = None
    messages = []
    if room_id:
        active_room = get_object_or_404(ChatRoom, id=room_id, team=team)
        if active_room.room_type == 'direct':
             other_member = active_room.members.exclude(id=request.user.id).first()
             active_room.display_name = other_member.get_full_name() if other_member else active_room.name
        else:
            active_room.display_name = active_room.name
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    elif channels.exists():
        active_room = channels.first()
        active_room.display_name = active_room.name
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    
    # Get team members for DM list
    existing_dm_partner_ids = []
    for dm in direct_messages:
        for member in dm.members.all():
            if member.id != request.user.id:
                existing_dm_partner_ids.append(member.id)
                
    team_members = TeamMember.objects.filter(team=team).exclude(user=request.user).exclude(user__id__in=existing_dm_partner_ids).select_related('user')
    
    # Check Google Chat connection
    from authentication.models import GoogleChatCredentials
    is_google_connected = GoogleChatCredentials.objects.filter(user=request.user).exists()

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
        team = get_object_or_404(teams_for(request.user), id=team_id)
    else:
        team = get_user_team(request.user)
    
    # Check if user is admin (allow access for testing, can add strict check later)
    if not is_team_member(request.user, team):
        return redirect('team:team_list')
    
    members = TeamMember.objects.filter(team=team).select_related('user')
    
    # Whether the current user may change roles: the team's creator, or
    # an admin, who manages every team.
    is_creator = team.creator == request.user or has_team_role(request.user, team, ('admin',))
    
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
    
    # Only the team's creator, or an admin, can change roles
    if team.creator != request.user and not has_team_role(request.user, team, ('admin',)):
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
    
    # Only the team's creator, or an admin, can remove members
    if team.creator != request.user and not has_team_role(request.user, team, ('admin',)):
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
    user_teams = teams_for(request.user)
    
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
             if not is_team_member(request.user, target_team):
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
            if not is_team_member(request.user, team):
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
                    from googleapiclient.discovery import build
                    from django.contrib.auth import get_user_model
                    
                    User = get_user_model()
                    user = User.objects.get(id=user_id)

                    creds_model = GoogleChatCredentials.objects.get(user=user)
                    creds = creds_model.google_credentials()
                    
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
            if not is_team_member(request.user, team):
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
    if not has_team_role(request.user, team):
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
    if not has_team_role(request.user, team, ('admin',)):
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
    
    team = get_object_or_404(teams_for(request.user), id=team_id)
    
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
    if not is_team_member(request.user, room.team):
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
    if not is_team_member(request.user, team):
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
    is_admin = has_team_role(request.user, team, ('admin',))
    
    if team.creator != request.user and not is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    team.is_archived = True
    team.save()
    
    return JsonResponse({'success': True, 'message': 'Team archived'})

@login_required
def get_manageable_teams(request):
    """Get teams where user has admin/manager/owner role for task assignment"""
    teams = [{'id': t.id, 'name': t.name}
             for t in teams_for(request.user).filter(is_archived=False)
             if has_team_role(request.user, t)]
    return JsonResponse({'teams': teams})

# ------------------- Google Chat Integration -------------------

from googleapiclient.discovery import build
from authentication.models import GoogleChatCredentials

def get_google_chat_service(user):
    """Build and return a Google Chat API service for the user"""
    try:
        creds_model = GoogleChatCredentials.objects.get(user=user)
        
        credentials = creds_model.google_credentials()
        
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
    task = get_object_or_404(
        Task.objects.exclude(team=None).select_related('team', 'created_by').prefetch_related('assignees__user', 'attachments'),
        id=task_id
    )
    
    # Check permissions and get role
    role = team_role(request.user, task.team)
    if role is None:
        return HttpResponseForbidden("Permission denied")

    # Determine edit permission
    # Editable if:
    # 1. User is the creator/assigner of the task
    # 2. User is an Admin or Manager of the team
    is_assigner = _is_creator(task, request.user)
    is_admin_or_manager = role in ['admin', 'manager']
    
    can_edit = is_assigner or is_admin_or_manager

    # Render template
    html = render_to_string('team/components/task_edit_form.html', {
        'task': task,
        'team': task.team,
        'can_edit': can_edit,
    }, request=request)
    
    return HttpResponse(html)
