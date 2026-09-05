from django.apps import AppConfig


class EmailAutomationConfig(AppConfig):
    """Migrations-only stub.

    The mail system (models, views, urls, services, signals, templates and
    static files) moved into the `marketing` app. Nothing is defined here any
    more — but the app must stay registered, because this package's own
    migration history and marketing's adoption migration declare dependencies
    on ('email_automation', ...). Dropping the app would make the migration
    graph unresolvable on every database that has already applied them.

    The models were re-pointed at marketing via a SeparateDatabaseAndState
    move, so this app owns no tables.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "email_automation"
    verbose_name = "Email Automation (migrations only)"
