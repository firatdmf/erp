from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketing'

    # This method is called when the app is ready.
    # This is how we import signals in Django.
    def ready(self):
        import marketing.signals
        # The mail system moved in from the old `email_automation` app; its
        # signals and background sender hang off this app's startup now.
        import marketing.signals_email

        # Start background scheduler for automatic email sending
        # Only in main process, not in reloader
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            from .email_scheduler import start_scheduler
            start_scheduler()
