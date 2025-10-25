from django.apps import AppConfig


class EmailAutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_automation'
    verbose_name = 'Email Automation'
    
    def ready(self):
        import email_automation.signals
        
        # Start background scheduler for automatic email sending
        # Only in main process, not in reloader
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            from .scheduler import start_scheduler
            start_scheduler()
