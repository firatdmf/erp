from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Notification, NotificationPreference
import json


@login_required
@require_http_methods(["GET"])
def get_notifications(request):
    """
    Get unread notification count and recent notifications.
    Returns JSON with count and list of notifications.
    """
    member = getattr(request.user, 'member', None)
    if not member:
        return JsonResponse({'success': False, 'error': 'No member profile'}, status=400)
    
    # Get unread count
    unread_count = Notification.objects.filter(recipient=member, is_read=False).count()
    
    # Get recent notifications (last 20)
    notifications = Notification.objects.filter(recipient=member).order_by('-created_at')[:20]
    
    notifications_data = []
    for notif in notifications:
        notifications_data.append({
            'id': notif.id,
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'link': notif.link,
            'icon': notif.icon,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat(),
            'time_ago': get_time_ago(notif.created_at),
        })
    
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'notifications': notifications_data,
    })


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read.
    """
    member = getattr(request.user, 'member', None)
    if not member:
        return JsonResponse({'success': False, 'error': 'No member profile'}, status=400)
    
    notification = get_object_or_404(Notification, id=notification_id, recipient=member)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    
    # Get new unread count
    unread_count = Notification.objects.filter(recipient=member, is_read=False).count()
    
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
    })


@login_required
@require_http_methods(["POST"])
def mark_all_read(request):
    """
    Mark all notifications as read for the current user.
    """
    member = getattr(request.user, 'member', None)
    if not member:
        return JsonResponse({'success': False, 'error': 'No member profile'}, status=400)
    
    Notification.objects.filter(recipient=member, is_read=False).update(is_read=True)
    
    return JsonResponse({
        'success': True,
        'unread_count': 0,
    })


@login_required
@require_http_methods(["POST"])
def save_push_subscription(request):
    """
    Save browser push notification subscription.
    """
    member = getattr(request.user, 'member', None)
    if not member:
        return JsonResponse({'success': False, 'error': 'No member profile'}, status=400)
    
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')
        
        if not subscription:
            return JsonResponse({'success': False, 'error': 'No subscription data'}, status=400)
        
        # Get or create notification preference
        pref, created = NotificationPreference.objects.get_or_create(member=member)
        pref.push_subscription = json.dumps(subscription)
        pref.save(update_fields=['push_subscription', 'updated_at'])
        
        return JsonResponse({'success': True, 'message': 'Subscription saved'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_notifications(request):
    """
    Toggle notification preferences for the current user.
    """
    member = getattr(request.user, 'member', None)
    if not member:
        return JsonResponse({'success': False, 'error': 'No member profile'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Get or create notification preference
        pref, created = NotificationPreference.objects.get_or_create(member=member)
        
        # Update preferences
        if 'receive_notifications' in data:
            pref.receive_notifications = data['receive_notifications']
        if 'receive_order_notifications' in data:
            pref.receive_order_notifications = data['receive_order_notifications']
        if 'receive_task_notifications' in data:
            pref.receive_task_notifications = data['receive_task_notifications']
        
        pref.save()
        
        return JsonResponse({
            'success': True,
            'receive_notifications': pref.receive_notifications,
            'receive_order_notifications': pref.receive_order_notifications,
            'receive_task_notifications': pref.receive_task_notifications,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


def get_time_ago(dt):
    """
    Return a human-readable time ago string.
    """
    now = timezone.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f'{minutes}m ago'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f'{days}d ago'
    else:
        return dt.strftime('%b %d')
