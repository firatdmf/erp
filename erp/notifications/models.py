from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from authentication.models import Member


class Notification(models.Model):
    """
    Notification model for storing user notifications.
    Used for new orders, task assignments, and task updates.
    """
    NOTIFICATION_TYPES = [
        ('new_order', 'New Order'),
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('task_comment', 'Task Comment'),
    ]
    
    # Who receives this notification
    recipient = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    # Notification details
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)  # URL to navigate on click
    icon = models.CharField(max_length=50, default='fa-bell')  # FontAwesome icon class
    
    # Generic relation to any model (Order, Task, etc.)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Status
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.notification_type}: {self.title} -> {self.recipient}"
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message='', link='', icon='fa-bell', content_object=None):
        """
        Helper method to create a notification
        """
        notification = cls(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            icon=icon,
        )
        
        if content_object:
            notification.content_type = ContentType.objects.get_for_model(content_object)
            notification.object_id = content_object.pk
        
        notification.save()
        return notification


class NotificationPreference(models.Model):
    """
    User preferences for receiving notifications.
    Only users with receive_notifications=True will get notifications.
    """
    member = models.OneToOneField(
        Member, 
        on_delete=models.CASCADE, 
        related_name='notification_preference'
    )
    
    # Master switch
    receive_notifications = models.BooleanField(default=True)
    
    # Per-type preferences
    receive_order_notifications = models.BooleanField(default=True)
    receive_task_notifications = models.BooleanField(default=True)
    
    # Browser push notification subscription
    push_subscription = models.TextField(blank=True, null=True)  # Stores JSON subscription data
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"NotificationPreference for {self.member}"
