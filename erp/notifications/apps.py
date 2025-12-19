from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    
    def ready(self):
        # Import and connect signals after all models are loaded
        from notifications.signals import connect_signals
        connect_signals()
