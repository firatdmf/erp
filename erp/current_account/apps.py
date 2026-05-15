from django.apps import AppConfig


class CurrentAccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "current_account"
    verbose_name = "Cari Hesap"

    def ready(self):
        import current_account.signals  # noqa: F401
