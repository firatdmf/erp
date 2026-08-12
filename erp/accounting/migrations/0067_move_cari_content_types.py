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
        _repoint(apps, schema_editor, db, new.pk, old.pk)
        new.delete(using=db)
        old.app_label = "accounting"
        old.save(using=db)


def backwards(apps, schema_editor):
    """Mirror of forwards, and it has to fold duplicates for the same reason.

    A blanket UPDATE back to current_account would hit the (app_label, model)
    unique constraint wherever a current_account row still exists — which is
    exactly the state a half-finished forwards run leaves behind, i.e. the one
    case a rollback actually gets used in.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    db = schema_editor.connection.alias

    for model in MODELS:
        current = ContentType.objects.using(db).filter(
            app_label="accounting", model=model).first()
        if current is None:
            continue

        stale = ContentType.objects.using(db).filter(
            app_label="current_account", model=model).first()
        if stale is not None:
            _repoint(apps, schema_editor, db, stale.pk, current.pk)
            stale.delete(using=db)

        current.app_label = "current_account"
        current.save(using=db)


# Through tables carrying permission grants. Existence-checked before use so
# this keeps working if the project ever swaps in a custom user model.
_GRANT_TABLES = [
    ("auth_group_permissions", "group_id"),
    ("auth_user_user_permissions", "user_id"),
]


def _move_grants(cursor, from_perm_id, to_perm_id):
    """Hand src's grants to dst, dropping rows that would duplicate."""
    for table, owner in _GRANT_TABLES:
        cursor.execute("select to_regclass(%s)", [table])
        if cursor.fetchone()[0] is None:
            continue
        cursor.execute(
            f"UPDATE {table} t SET permission_id = %s "
            f"WHERE t.permission_id = %s AND NOT EXISTS ("
            f"  SELECT 1 FROM {table} d "
            f"  WHERE d.{owner} = t.{owner} AND d.permission_id = %s)",
            [to_perm_id, from_perm_id, to_perm_id],
        )
        cursor.execute(f"DELETE FROM {table} WHERE permission_id = %s",
                       [from_perm_id])


def _repoint(apps, schema_editor, db, from_id, to_id):
    """Point everything that references content type `from_id` at `to_id`.

    Permissions cannot simply be re-pointed. Both content types own an
    auto-created add/change/delete/view set, and auth_permission is unique on
    (content_type_id, codename), so bulk-updating them collides:

        duplicate key value violates unique constraint
        "auth_permission_content_type_id_codename_..."
        DETAIL: Key (content_type_id, codename)=(152, add_invoice) already exists

    That is precisely what aborted a deploy mid-flight, after the preceding
    migration had already committed its table renames. Where the destination
    already owns a codename we keep its row and delete the duplicate — but only
    after handing over whatever groups or users had been granted it, since a
    bare delete would silently revoke access.
    """
    Permission = apps.get_model("auth", "Permission")
    cursor = schema_editor.connection.cursor()
    surviving = dict(
        Permission.objects.using(db).filter(content_type_id=to_id)
        .values_list("codename", "id"))

    for perm in Permission.objects.using(db).filter(content_type_id=from_id):
        twin = surviving.get(perm.codename)
        if twin is None:
            perm.content_type_id = to_id
            perm.save(using=db, update_fields=["content_type_id"])
            surviving[perm.codename] = perm.id
        else:
            _move_grants(cursor, perm.id, twin)
            perm.delete(using=db)

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
