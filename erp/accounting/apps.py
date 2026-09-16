from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        # Ledger signals (current account code assignment, supplier current account creation,
        # legacy AR/AP mirroring) — moved here with the current_account merge.
        import accounting.signals_accounts  # noqa: F401
        # General-ledger posting. Imported second so that a movement is
        # mirrored onto its paired account BEFORE either half is posted —
        # the mirror is itself a saved movement, so it posts through this
        # same receiver and needs no special case.
        import accounting.signals_ledger    # noqa: F401
