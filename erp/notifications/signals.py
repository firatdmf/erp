from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Notification, NotificationPreference


def get_notification_recipients(notification_type):
    """
    Get list of members who should receive this notification type.
    Only returns members with receive_notifications=True and the specific type enabled.
    """
    from authentication.models import Member
    
    # Get all members with notification preferences that allow this type
    preferences = NotificationPreference.objects.filter(
        receive_notifications=True
    )
    
    if notification_type == 'new_order':
        preferences = preferences.filter(receive_order_notifications=True)
    elif notification_type in ['task_assigned', 'task_updated']:
        preferences = preferences.filter(receive_task_notifications=True)
    
    member_ids = preferences.values_list('member_id', flat=True)
    
    # Also include members who don't have a preference record yet (default behavior)
    members_with_prefs = NotificationPreference.objects.values_list('member_id', flat=True)
    all_members = Member.objects.all()
    
    # Members without preferences are included by default
    members_without_prefs = all_members.exclude(id__in=members_with_prefs)
    
    # Combine members with explicit permission and those without preferences
    return list(Member.objects.filter(id__in=member_ids)) + list(members_without_prefs)


# ============================================================
# ORDER SIGNALS - Using lazy import to avoid circular imports
# ============================================================

def create_order_notification_handler(sender, instance, created, **kwargs):
    """
    Create notifications when a new order is created.
    Notifies all members who have order notifications enabled.
    """
    if not created:
        return
    
    print(f"📦 Order signal triggered for Order #{instance.pk}")
    
    # Don't notify for orders without an order_number (internal orders)
    # Only notify for web orders or orders with explicit order numbers
    order_number = instance.order_number or f"#{instance.pk}"
    
    # Get recipients
    recipients = get_notification_recipients('new_order')
    
    for member in recipients:
        Notification.create_notification(
            recipient=member,
            notification_type='new_order',
            title=f'New order received - {order_number}',
            message=f'Order from {instance.get_client()}',
            link=reverse('operating:order_detail', kwargs={'pk': instance.pk}),
            icon='fa-shopping-cart',
            content_object=instance,
        )
    
    print(f"✓ Created order notifications for {len(recipients)} recipients - Order {order_number}")


# ============================================================
# TASK SIGNALS
# ============================================================

def create_task_notification_handler(sender, instance, created, **kwargs):
    """
    Create notifications for task events:
    - Task assigned: Notify the assigned member
    - Task updated: Notify the assigned member if they weren't the one updating
    """
    print(f"📋 Task signal triggered for Task #{instance.pk} - created={created}")
    
    if created:
        # New task created - notify if someone is assigned
        if instance.member and instance.created_by:
            print(f"   Task member: {instance.member}, created_by: {instance.created_by}")
            # Only notify if the task was assigned to someone else
            if instance.member != instance.created_by:
                # Check if recipient has notifications enabled
                pref = NotificationPreference.objects.filter(member=instance.member).first()
                if pref and not pref.receive_task_notifications:
                    print(f"   Skipping: notifications disabled for {instance.member}")
                    return
                if pref and not pref.receive_notifications:
                    print(f"   Skipping: all notifications disabled for {instance.member}")
                    return
                
                Notification.create_notification(
                    recipient=instance.member,
                    notification_type='task_assigned',
                    title=f'Task assigned: {instance.name}',
                    message=f'Assigned by {instance.created_by}',
                    link=reverse('todo:task_detail', kwargs={'task_id': instance.pk}),
                    icon='fa-tasks',
                    content_object=instance,
                )
                print(f"✓ Created task assignment notification for {instance.member}")
            else:
                print(f"   Skipping: task assigned to self")
        else:
            print(f"   Skipping: no member ({instance.member}) or created_by ({instance.created_by})")


# Signal for task activity (priority change, due date change, etc.)
def create_task_activity_notification_handler(sender, instance, created, **kwargs):
    """
    Create notifications when task activity is logged (from existing TaskActivity model).
    Notifies the assigned member about changes.
    """
    if not created:
        return
    
    task = instance.task
    activity_type = instance.activity_type
    actor = instance.user  # Who made the change
    
    print(f"📝 TaskActivity signal triggered - {activity_type} for Task #{task.pk}")
    
    # Don't notify for 'created' activity (handled by create_task_notification)
    if activity_type == 'created':
        print(f"   Skipping: 'created' activity handled by task signal")
        return
    
    # Create notification message based on activity type
    activity_messages = {
        'completed': 'Task completed',
        'reopened': 'Task reopened',
        'status_changed': f'Status changed to {instance.new_value}',
        'priority_changed': f'Priority changed to {instance.new_value}',
        'due_date_changed': f'Due date changed to {instance.new_value}',
        'assigned': f'Task reassigned',
        'description_updated': 'Description updated',
        'name_updated': 'Task name updated',
    }
    
    title = activity_messages.get(activity_type, 'Task updated')
    
    # Notify assignee if they're not the actor
    if task.member and task.member != actor:
        pref = NotificationPreference.objects.filter(member=task.member).first()
        if not pref or (pref.receive_notifications and pref.receive_task_notifications):
            Notification.create_notification(
                recipient=task.member,
                notification_type='task_updated',
                title=f'{title}: {task.name}',
                message=f'Updated by {actor}' if actor else 'Task was updated',
                link=reverse('todo:task_detail', kwargs={'task_id': task.pk}),
                icon='fa-edit',
                content_object=task,
            )
            print(f"✓ Created task update notification for assignee {task.member} - {activity_type}")
    
    # Also notify task creator if different from actor and assignee
    if task.created_by and task.created_by != actor and task.created_by != task.member:
        pref = NotificationPreference.objects.filter(member=task.created_by).first()
        if not pref or (pref.receive_notifications and pref.receive_task_notifications):
            Notification.create_notification(
                recipient=task.created_by,
                notification_type='task_updated',
                title=f'{title}: {task.name}',
                message=f'Updated by {actor}' if actor else 'Task was updated',
                link=reverse('todo:task_detail', kwargs={'task_id': task.pk}),
                icon='fa-edit',
                content_object=task,
            )
            print(f"✓ Created task update notification for creator {task.created_by} - {activity_type}")


# ============================================================
# TASK COMMENT SIGNALS
# ============================================================

def create_task_comment_notification_handler(sender, instance, created, **kwargs):
    """
    Create notification when someone comments on a task.
    Notifies the assigned member and task creator (if different from commenter).
    """
    if not created:
        return
    
    task = instance.task
    commenter = instance.author  # Who wrote the comment
    
    print(f"💬 TaskComment signal triggered - Comment on Task #{task.pk} by {commenter}")
    
    # Notify task assignee if they're not the commenter
    if task.member and task.member != commenter:
        # Check if recipient has notifications enabled
        pref = NotificationPreference.objects.filter(member=task.member).first()
        if pref and not pref.receive_task_notifications:
            print(f"   Skipping: notifications disabled for {task.member}")
            return
        if pref and not pref.receive_notifications:
            print(f"   Skipping: all notifications disabled for {task.member}")
            return
        
        Notification.create_notification(
            recipient=task.member,
            notification_type='task_comment',
            title=f'New comment: {task.name}',
            message=f'{commenter} commented on your task',
            link=reverse('todo:task_detail', kwargs={'task_id': task.pk}),
            icon='fa-comment',
            content_object=task,
        )
        print(f"✓ Created comment notification for task assignee {task.member}")
    
    # Also notify task creator if they're different from both commenter and assignee
    if task.created_by and task.created_by != commenter and task.created_by != task.member:
        pref = NotificationPreference.objects.filter(member=task.created_by).first()
        if pref and not pref.receive_task_notifications:
            return
        if pref and not pref.receive_notifications:
            return
        
        Notification.create_notification(
            recipient=task.created_by,
            notification_type='task_comment',
            title=f'New comment: {task.name}',
            message=f'{commenter} commented on task you created',
            link=reverse('todo:task_detail', kwargs={'task_id': task.pk}),
            icon='fa-comment',
            content_object=task,
        )
        print(f"✓ Created comment notification for task creator {task.created_by}")


def connect_signals():
    """Connect signals after models are loaded to avoid circular imports."""
    from operating.models import Order
    from todo.models import Task, TaskActivity, TaskComment
    
    # Connect Order signal
    post_save.connect(create_order_notification_handler, sender=Order)
    print("📡 Connected Order notification signal")
    
    # Connect Task signal  
    post_save.connect(create_task_notification_handler, sender=Task)
    print("📡 Connected Task notification signal")
    
    # Connect TaskActivity signal (for status changes, priority changes, etc.)
    post_save.connect(create_task_activity_notification_handler, sender=TaskActivity)
    print("📡 Connected TaskActivity notification signal")
    
    # Connect TaskComment signal
    post_save.connect(create_task_comment_notification_handler, sender=TaskComment)
    print("📡 Connected TaskComment notification signal")
