from django.contrib import admin
from .models import Team, TeamMember, TeamRole, TeamTask, TeamMessage, TeamMeeting

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at')
    search_fields = ('name', 'creator__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'joined_at')
    list_filter = ('role', 'team')
    search_fields = ('user__username', 'team__name')

@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'team')
    search_fields = ('name', 'team__name')

@admin.register(TeamTask)
class TeamTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority', 'team')
    search_fields = ('title', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TeamMessage)
class TeamMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'team', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'team__name')
    readonly_fields = ('created_at', 'read_at')

@admin.register(TeamMeeting)
class TeamMeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'scheduled_at', 'status')
    list_filter = ('status', 'team')
    search_fields = ('title', 'organizer__username')
    readonly_fields = ('created_at', 'updated_at')
