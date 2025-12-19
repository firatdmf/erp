from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.get_notifications, name='get_notifications'),
    path('<int:notification_id>/read/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('push-subscription/', views.save_push_subscription, name='save_push_subscription'),
    path('toggle/', views.toggle_notifications, name='toggle_notifications'),
]
