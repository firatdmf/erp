from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
import json

from .models import Team, TeamMember, TeamTask, TeamMessage, TeamMeeting, FavoriteTeam, ChatRoom

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
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        assigned_to_id = request.POST.get('assigned_to')
        due_date = request.POST.get('due_date') or None
        priority = request.POST.get('priority', 'medium')
        status = request.POST.get('status', 'todo')
        
        assigned_to = get_object_or_404(User, id=assigned_to_id)
        
        TeamTask.objects.create(
            team=team,
            title=title,
            description=description,
            assigned_by=request.user,
            assigned_to=assigned_to,
            due_date=due_date,
            priority=priority,
            status=status
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Task created successfully'})
        
        return redirect('team:team_tasks')
    
    # Group tasks by status for Kanban columns
    all_tasks = TeamTask.objects.filter(team=team).select_related('assigned_to', 'assigned_by')
    
    context = {
        'team': team,
        'members': TeamMember.objects.filter(team=team).select_related('user'),
        'pending_tasks': all_tasks.filter(status='todo'),
        'in_progress_tasks': all_tasks.filter(status='in_progress'),
        'review_tasks': all_tasks.filter(status='review'),
        'completed_tasks': all_tasks.filter(status='done'),
        'page_title': f'{team.name} Tasks',
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
    
    task.status = 'completed'
    task.completed_at = timezone.now()
    task.save()
    
    return JsonResponse({'success': True, 'message': 'Task marked as completed'})

@login_required
@require_http_methods(["POST"])
def update_task_status(request, task_id):
    """Update task status (for Kanban drag-and-drop)"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check if user is team member
    if not TeamMember.objects.filter(team=task.team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    new_status = request.POST.get('status')
    valid_statuses = ['pending', 'in_progress', 'review', 'completed']
    
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    task.status = new_status
    if new_status == 'completed':
        task.completed_at = timezone.now()
    task.save()
    
    return JsonResponse({'success': True, 'message': f'Task status updated to {new_status}'})

@login_required
@require_http_methods(["POST"])
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permission - only assigned_by can delete
    if task.assigned_by != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    task.delete()
    return JsonResponse({'success': True, 'message': 'Task deleted'})

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
    
    # Get active room
    active_room = None
    messages = []
    if room_id:
        active_room = get_object_or_404(ChatRoom, id=room_id, team=team)
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    elif channels.exists():
        active_room = channels.first()
        messages = active_room.messages.select_related('sender').prefetch_related('attachments').order_by('created_at')
    
    # Get team members for DM list (exclude current user)
    team_members = TeamMember.objects.filter(team=team).exclude(user=request.user).select_related('user')
    
    context = {
        'team': team,
        'user_teams': user_teams,
        'channels': channels,
        'direct_messages': direct_messages,
        'team_members': team_members,
        'active_room': active_room,
        'messages': messages,
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
def team_meetings(request):
    """Display and schedule team meetings"""
    team = get_user_team(request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        scheduled_at = request.POST.get('scheduled_at')
        duration_minutes = request.POST.get('duration_minutes', 60)
        meeting_link = request.POST.get('meeting_link', '')
        location = request.POST.get('location', '')
        participant_ids = request.POST.getlist('participants[]')
        
        meeting = TeamMeeting.objects.create(
            team=team,
            title=title,
            description=description,
            organizer=request.user,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            meeting_link=meeting_link,
            location=location
        )
        
        # Add participants
        participants = User.objects.filter(id__in=participant_ids)
        meeting.participants.set(participants)
        meeting.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Meeting scheduled successfully'})
        
        return redirect('team:team_meetings')
    
    upcoming_meetings = TeamMeeting.objects.filter(team=team, status='scheduled').order_by('scheduled_at')[:10]
    all_meetings = TeamMeeting.objects.filter(team=team).order_by('-scheduled_at')
    members = TeamMember.objects.filter(team=team).select_related('user')
    
    context = {
        'team': team,
        'upcoming_meetings': upcoming_meetings,
        'all_meetings': all_meetings,
        'members': members,
        'page_title': 'Team Meetings',
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
    """Search for users to add to team"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        models.Q(username__icontains=query) | 
        models.Q(first_name__icontains=query) | 
        models.Q(last_name__icontains=query) | 
        models.Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
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
@require_http_methods(["POST"])
def add_member(request):
    """Add a member to the team"""
    team = get_user_team(request.user)
    
    # Check admin permission
    if not TeamMember.objects.filter(team=team, user=request.user, role__in=['admin', 'manager']).exists():
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
        
        return JsonResponse({'success': True, 'room_id': room.id, 'message': 'Conversation started'})
    
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
    
    # Add all team members to the channel
    for member in team.members.all():
        room.members.add(member)
    
    return JsonResponse({'success': True, 'room_id': room.id, 'message': 'Channel created'})


@login_required
@require_http_methods(["POST"])
def send_chat_message(request):
    """Send a message to a chat room"""
    from .models import ChatRoom, ChatMessage
    
    room_id = request.POST.get('room_id')
    content = request.POST.get('content')
    
    if not room_id or not content:
        return JsonResponse({'success': False, 'error': 'Room and content required'}, status=400)
    
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check if user is team member
    if not TeamMember.objects.filter(team=room.team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    message = ChatMessage.objects.create(
        room=room,
        sender=request.user,
        content=content
    )
    
    # Update room's updated_at
    room.save()
    
    return JsonResponse({
        'success': True,
        'message_id': message.id,
        'sender': request.user.get_full_name(),
        'content': content,
        'created_at': message.created_at.isoformat()
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
