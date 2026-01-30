from django.urls import path
from . import views

app_name = 'team'

urlpatterns = [
    # Team management
    path('members/', views.team_list, name='team_list'),
    path('tasks/', views.team_tasks, name='team_tasks'),
    path('messages/', views.team_messages, name='team_messages'),
    path('roles/', views.team_roles, name='team_roles'),
    path('create/', views.create_team, name='create_team'),
    path('search-users/', views.search_users, name='search_users'),
    path('add-member/', views.add_member, name='add_member'),
    path('meetings/', views.team_meetings, name='team_meetings'),
    
    # Task operations
    path('task/<int:task_id>/complete/', views.complete_task, name='complete_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('task/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    
    # Message operations
    path('message/send/', views.send_message, name='send_message'),
    path('messages/user/<int:user_id>/', views.get_user_messages, name='get_user_messages'),
    
    # Role operations
    path('member/<int:member_id>/role/', views.update_member_role, name='update_member_role'),
    
    # Meeting operations
    path('meeting/create/', views.create_meeting, name='create_meeting'),
    path('meeting/<int:meeting_id>/delete/', views.delete_meeting, name='delete_meeting'),
    
    # Invitation operations
    path('invitations/', views.pending_invitations, name='pending_invitations'),
    path('invitation/<str:token>/respond/', views.respond_invitation, name='respond_invitation'),
    path('<int:team_id>/invitations/', views.get_team_invitations, name='get_team_invitations'),
    
    # Chat operations
    path('chat/room/create/', views.create_chat_room, name='create_chat_room'),
    path('chat/message/send/', views.send_chat_message, name='send_chat_message'),
    
    # Team actions
    path('<int:team_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('<int:team_id>/archive/', views.archive_team, name='archive_team'),
]
