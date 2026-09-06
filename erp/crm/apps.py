from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'

    def ready(self):
        import crm.signals

        # Stamp created_by on every new Company/Contact, whichever path
        # made it (list screens, detail sidebars, the order form's
        # inline quick-create).
        from erp.ownership import register
        from .models import Company, Contact
        register(Company, Contact)
