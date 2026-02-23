from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Team(models.Model):
    """Team model to group users together"""
    ICON_COLORS = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('orange', 'Orange'),
        ('purple', 'Purple'),
        ('red', 'Red'),
        ('teal', 'Teal'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_teams')
    icon_color = models.CharField(max_length=20, choices=ICON_COLORS, default='blue')
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    members = models.ManyToManyField(User, through='TeamMember', related_name='teams')
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def get_task_count(self):
        return self.tasks.exclude(status='completed').count()
    
    def get_message_count(self):
        return self.chat_rooms.aggregate(models.Sum('messages__id'))['messages__id__sum'] or 0


class TeamMember(models.Model):
    """Through model for Team-User relationship with role information"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('member', 'Member'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='member_objects')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('team', 'user')
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class TeamRole(models.Model):
    """Custom role model for team permissions"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='custom_roles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, help_text="JSON object with permissions")
    
    class Meta:
        unique_together = ('team', 'name')
    
    def __str__(self):
        return f"{self.team.name} - {self.name}"


class TeamBoardColumn(models.Model):
    """Dynamic columns for Kanban board"""
    COLOR_CHOICES = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('orange', 'Orange'),
        ('purple', 'Purple'),
        ('red', 'Red'),
        ('gray', 'Gray'),
        ('pink', 'Pink'),
        ('teal', 'Teal'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=50)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='blue')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('team', 'title')
    
    def __str__(self):
        return f"{self.team.name} - {self.title}"


class TeamTask(models.Model):
    """Task assignment model for team members"""
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('done', 'Done'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tasks')
    column = models.ForeignKey(TeamBoardColumn, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_team_tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_team_tasks_legacy')
    assignees = models.ManyToManyField(User, related_name='team_tasks', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    google_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of the task in Google Tasks")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.assigned_to.get_full_name()}"


class TeamTaskAttachment(models.Model):
    """Files attached to team tasks (stored in Google Drive)"""
    task = models.ForeignKey(TeamTask, on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255)
    drive_file_id = models.CharField(max_length=255)
    drive_link = models.URLField(max_length=500)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

    def get_download_url(self):
        """Returns direct download link"""
        return f"https://drive.google.com/uc?export=download&id={self.drive_file_id}"


class TeamTaskComment(models.Model):
    """Comments on team tasks"""
    task = models.ForeignKey(TeamTask, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"


class TeamMessage(models.Model):
    """Direct messaging between team members"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_team_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_team_messages')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    attachment_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.get_full_name()} -> {self.recipient.get_full_name()}"


class TeamMeeting(models.Model):
    """Meeting scheduling for team members"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='meetings', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_team_meetings')
    participants = models.ManyToManyField(User, related_name='team_meetings')
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.IntegerField(default=60)
    meeting_link = models.URLField(blank=True, help_text="Zoom/Google Meet link")
    location = models.CharField(max_length=255, blank=True, help_text="Physical location if applicable")
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('scheduled', 'Scheduled'), ('ongoing', 'Ongoing'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        default='scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_at']
    
    def __str__(self):
        return f"{self.title} - {self.scheduled_at}"


class TeamInvitation(models.Model):
    """Invitation model for tracking pending team invitations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_team_invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_team_invitations')
    role = models.CharField(max_length=20, choices=TeamMember.ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, help_text="Optional message to the invitee")
    token = models.CharField(max_length=64, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invitation: {self.invited_user.get_full_name()} to {self.team.name}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            from datetime import timedelta
            from django.utils import timezone
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at if self.expires_at else False
    
    def accept(self):
        """Accept the invitation and add user to team"""
        from django.utils import timezone
        if self.status != 'pending':
            return False
        if self.is_expired():
            self.status = 'expired'
            self.save()
            return False
        
        TeamMember.objects.get_or_create(
            team=self.team,
            user=self.invited_user,
            defaults={'role': self.role}
        )
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        return True
    
    def decline(self):
        """Decline the invitation"""
        from django.utils import timezone
        if self.status != 'pending':
            return False
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()
        return True


class FavoriteTeam(models.Model):
    """Track user's favorite teams"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'team')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.team.name}"


class ChatRoom(models.Model):
    """Chat room for team messaging"""
    ROOM_TYPES = [
        ('channel', 'Channel'),
        ('group', 'Group'),
        ('direct', 'Direct Message'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='chat_rooms')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='channel')
    members = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_chat_rooms')
    is_default = models.BooleanField(default=False, help_text="Default room for new team members")
    google_space_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Chat Space ID if connected")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"#{self.name} ({self.team.name})"
    
    def get_unread_count(self, user):
        last_read = self.read_markers.filter(user=user).first()
        if last_read:
            return self.messages.filter(created_at__gt=last_read.last_read_at).exclude(sender=user).count()
        return self.messages.exclude(sender=user).count()


class ChatMessage(models.Model):
    """Individual chat message"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.content[:50]}"


class ChatFile(models.Model):
    """File attachment for chat"""
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='files')
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_chat_files')
    file = models.FileField(upload_to='chat_uploads/%Y/%m/%d/', null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.file_name

class ChatTypingStatus(models.Model):
    """Transient model to track who is typing in which room"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='typing_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='typing_statuses')
    last_typed = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('room', 'user')


class ChatReadMarker(models.Model):
    """Track when user last read a chat room"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='read_markers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_read_markers')
    last_read_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('room', 'user')
    
class TeamTaskHistory(models.Model):
    """History log for TeamTask"""
    EVENT_TYPES = [
        ('status_change', 'Status Change'),
        ('comment_added', 'Comment Added'),
        ('priority_change', 'Priority Change'),
        ('created', 'Task Created'),
    ]

    task = models.ForeignKey(TeamTask, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_history')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.first_name} - {self.event_type}"
