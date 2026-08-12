from django.apps import AppConfig


class CurrentAccountConfig(AppConfig):
    """Migrations-only stub.

    The ledger itself (models, views, services, signals, templates) moved
    into the `accounting` app. Nothing is defined here any more — but the
    app must stay registered, because migrations in `operating` and this
    package's own history declare dependencies on ('current_account', ...).
    Dropping the app would make the migration graph unresolvable on every
    database that has already applied them.

    The models were re-pointed at accounting via a SeparateDatabaseAndState
    move, so this app owns no tables.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "current_account"
    verbose_name = "Current Account (migrations only)"
