"""Name Firat as the creator of every supplier raised before the column.

crm.0021 gave Supplier a created_by, NULL on every existing row, and
SupplierUpdate treats a NULL creator as admin-only (erp.ownership). Every
supplier on the books was in fact added by Firat, so rather than leave
eleven records that only an admin may edit, this says who made them.

Only rows still NULL are touched, and only where a user named "firat"
exists; a fresh database, or the test one, has nothing to do.
"""
from django.db import migrations

CREATOR_USERNAME = "firat"


def name_firat_as_creator(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Supplier = apps.get_model("crm", "Supplier")
    firat = User.objects.filter(username=CREATOR_USERNAME).first()
    if firat is None:
        return
    Supplier.objects.filter(created_by__isnull=True).update(created_by=firat)


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0021_supplier_created_by"),
    ]

    operations = [
        migrations.RunPython(name_firat_as_creator, migrations.RunPython.noop),
    ]
