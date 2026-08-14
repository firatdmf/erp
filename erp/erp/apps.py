from django.apps import AppConfig


class ErpConfig(AppConfig):
    """Config for the project package itself, which is also an installed app.

    Exists so project-wide system checks have somewhere to register from —
    they belong to no single feature app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "erp"

    def ready(self):
        from django.core.checks import register
        from .template_lint import check_template_comments

        register(check_template_comments, "templates")
