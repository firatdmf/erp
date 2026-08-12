from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        # Ledger signals (cari code assignment, supplier cari creation,
        # legacy AR/AP mirroring) — moved here with the current_account merge.
        import accounting.signals_accounts  # noqa: F401
