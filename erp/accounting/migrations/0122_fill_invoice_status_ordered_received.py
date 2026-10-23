"""Purchases say what happened to them: draft → ordered, issued → received.

The paid statuses were never set (payments settle the account, not one
purchase), so only those two are renamed. The purchase history's status
entries are renamed with them, so an old change reads the way a new one does.
"""
from django.db import migrations

RENAMES = {"draft": "ordered", "issued": "received"}


def forwards(apps, schema_editor):
    Invoice = apps.get_model("accounting", "Invoice")
    PurchaseChange = apps.get_model("accounting", "PurchaseChange")
    for old, new in RENAMES.items():
        Invoice.objects.filter(status=old).update(status=new)
        PurchaseChange.objects.filter(field="status", old_value=old).update(old_value=new)
        PurchaseChange.objects.filter(field="status", new_value=old).update(new_value=new)


def backwards(apps, schema_editor):
    Invoice = apps.get_model("accounting", "Invoice")
    PurchaseChange = apps.get_model("accounting", "PurchaseChange")
    for old, new in RENAMES.items():
        Invoice.objects.filter(status=new).update(status=old)
        PurchaseChange.objects.filter(field="status", old_value=new).update(old_value=old)
        PurchaseChange.objects.filter(field="status", new_value=new).update(new_value=old)


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0121_invoice_status_ordered_received"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
