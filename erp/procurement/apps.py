from django.apps import AppConfig


class ProcurementConfig(AppConfig):
    """Migrations-only stub.

    Purchasing (models, views, forms, urls, admin and templates) moved into
    the `operating` app. Nothing is defined here any more — but the app must
    stay registered, because this package's own migration history and
    operating's adoption migration declare dependencies on
    ('procurement', ...). Dropping the app would make the migration graph
    unresolvable on every database that has already applied them.

    The models were re-pointed at operating via a SeparateDatabaseAndState
    move, so this app owns no tables.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "procurement"
    verbose_name = "Procurement (migrations only)"
