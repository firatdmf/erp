from django.db import migrations


MODELS = [
    "emailaccount",
    "emailtemplate",
    "emailcampaign",
    "sentemail",
    "receivedemail",
    "email",
    "emailattachment",
]


def forwards(apps, schema_editor):
    _repoint(apps, "email_automation", "marketing")


def backwards(apps, schema_editor):
    _repoint(apps, "marketing", "email_automation")


def _repoint(apps, old_label, new_label):
    """Move the mail content types across, carrying their permissions.

    Content-type rows are pointed at by auth_permission, django_admin_log and
    every generic foreign key, so they are updated in place rather than
    recreated — a delete-and-recreate would silently strip the permissions
    already granted to roles and drop the admin history for these models.

    Django creates content types lazily after migrate, so a row may already
    exist under the target label on a database where the app has been loaded
    since. That row has no history worth keeping, so it gives way to the one
    being moved.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    for model in MODELS:
        ContentType.objects.filter(app_label=new_label, model=model).delete()
        ContentType.objects.filter(app_label=old_label, model=model).update(
            app_label=new_label
        )


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("marketing", "0080_adopt_mail_models_from_email_automation"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
