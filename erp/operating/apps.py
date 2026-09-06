from django.apps import AppConfig


class OperatingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operating'


    # Below added for signals.py
    def ready(self):
        import operating.signals # ensures signals are registered
        import operating.audit   # order audit trail signals

        # Stamp created_by on every new Order, whichever path made it.
        from erp.ownership import register
        from .models import Order
        register(Order)