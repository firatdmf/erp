from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketing'

    # This method is called when the app is ready.
    # This is how we import signals in Django.
    def ready(self):
        import marketing.signals
