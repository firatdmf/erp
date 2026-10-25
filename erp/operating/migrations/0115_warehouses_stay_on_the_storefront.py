"""Keep every warehouse there is on the storefront.

Until now the storefront counted every warehouse's stock. A warehouse made
from here on starts off it, but the ones that exist keep showing what they
always showed: switching one off is a decision for its own edit page.
"""
from django.db import migrations


def switch_on(apps, schema_editor):
    Warehouse = apps.get_model("operating", "Warehouse")
    Warehouse.objects.update(on_storefront=True)


def switch_off(apps, schema_editor):
    Warehouse = apps.get_model("operating", "Warehouse")
    Warehouse.objects.update(on_storefront=False)


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0114_warehouse_storefront"),
    ]

    operations = [
        migrations.RunPython(switch_on, switch_off),
    ]
