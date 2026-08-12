"""Re-label the cari ContentType rows from current_account to accounting.

CariMovement.source_type is a ContentType foreign key, and live rows point at
the `current_account | invoice` / `current_account | order` style entries. Once
the models belong to `accounting`, ContentType.objects.get_for_model() returns
a different row, so lookups like services._order_movement() would silently stop
matching the movements they wrote.

The app_label is UPDATEd in place rather than deleted and recreated, which
keeps the content-type ids stable — auth_permission and django_admin_log both
reference them by id, and recreating would orphan every permission granted on
these models.

Runs after post_migrate on a fresh database might already have created
`accounting`-labelled rows for the same models; where that has happened the
duplicate is folded into the surviving row before the rename, so the
(app_label, model) unique constraint holds either way.
"""
from django.db import migrations

MODELS = [
    "cariaccount", "carimovement", "carisettings", "invoice",
    "invoiceitem", "payment", "paymentallocation", "checkorpromissorynote",
]


def forwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    db = schema_editor.connection.alias

    for model in MODELS:
        old = ContentType.objects.using(db).filter(
            app_label="current_account", model=model).first()
        if old is None:
            continue

        new = ContentType.objects.using(db).filter(
            app_label="accounting", model=model).first()

        if new is None:
            # Normal path: just relabel, ids stay put.
            old.app_label = "accounting"
            old.save(using=db)
            continue

        # A row for the new label already exists. Move every reference onto
        # the older id, then drop the newcomer so the unique constraint holds.
        _repoint(apps, db, new.pk, old.pk)
        new.delete(using=db)
        old.app_label = "accounting"
        old.save(using=db)


def backwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    db = schema_editor.connection.alias
    ContentType.objects.using(db).filter(
        app_label="accounting", model__in=MODELS
    ).update(app_label="current_account")


def _repoint(apps, db, from_id, to_id):
    """Point everything that references content type `from_id` at `to_id`."""
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.using(db).filter(content_type_id=from_id).update(
        content_type_id=to_id)

    try:
        LogEntry = apps.get_model("admin", "LogEntry")
    except LookupError:
        pass
    else:
        LogEntry.objects.using(db).filter(content_type_id=from_id).update(
            content_type_id=to_id)

    CariMovement = apps.get_model("accounting", "CariMovement")
    CariMovement.objects.using(db).filter(source_type_id=from_id).update(
        source_type_id=to_id)


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0066_cariaccount_carimovement_invoice_payment_invoiceitem_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
