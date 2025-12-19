from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__user__username']
    readonly_fields = ['created_at', 'content_type', 'object_id']
    ordering = ['-created_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['member', 'receive_notifications', 'receive_order_notifications', 'receive_task_notifications']
    list_filter = ['receive_notifications', 'receive_order_notifications', 'receive_task_notifications']
    search_fields = ['member__user__username']
