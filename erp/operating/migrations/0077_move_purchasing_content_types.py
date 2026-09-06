from django.db import migrations


MODELS = [
    "purchaserequest",
    "purchaserequestitem",
    "requestforquotation",
    "purchaseorder",
    "purchaseorderitem",
]


def forwards(apps, schema_editor):
    _repoint(apps, "procurement", "operating")


def backwards(apps, schema_editor):
    _repoint(apps, "operating", "procurement")


def _repoint(apps, old_label, new_label):
    """Move the purchasing content types across, carrying their permissions.

    Same reasoning as marketing/0081: content-type rows are pointed at by
    auth_permission and django_admin_log, so they are updated in place rather
    than recreated, and any row Django has already created lazily under the
    target label gives way to the one being moved.
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
        ("operating", "0076_adopt_purchasing_from_procurement"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
