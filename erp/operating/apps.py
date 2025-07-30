from django.apps import AppConfig


class OperatingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operating'


    # Below added for signals.py
    def ready(self):
        import operating.signals