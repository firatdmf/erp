"""Stamp every existing stock item with what its SKU currently costs.

This is the one moment the backfill is accurate. WarehouseProduct
.cost_usd is a last-purchase price — intake overwrites it whenever a
batch arrives at a new price — so today it still equals what was
actually paid for very nearly every stock item on the shelves: all 4,643
Ergene stock items arrived in one load between 2026-08-31 and 2026-09-05, and
exactly one SKU of 841 has been received twice. After the next
repurchase the old cost is gone and no backfill can recover it.

Stock items whose SKU carries no cost are left null rather than guessed at.
The balance sheet counts those separately (see
accounting.services_ledger._inventory_value) so unvalued stock cannot
read as free stock.

The reverse blanks the column, which makes the forward pass re-runnable.
"""
from django.db import migrations
from django.db.models import OuterRef, Subquery


def stamp_cost(apps, schema_editor):
    Roll = apps.get_model("operating", "WarehouseProductRoll")
    Product = apps.get_model("operating", "WarehouseProduct")
    # One UPDATE with a correlated subquery rather than a save() per row:
    # there are thousands of stock items and this runs in the deploy's migrate
    # step. A plain F("product__cost_usd") cannot be used — Django refuses
    # joined field references in UPDATE.
    Roll.objects.filter(
        unit_cost_base__isnull=True,
        product__cost_usd__isnull=False,
    ).update(
        unit_cost_base=Subquery(
            Product.objects.filter(pk=OuterRef("product_id")).values("cost_usd")[:1]
        )
    )


def blank_cost(apps, schema_editor):
    Roll = apps.get_model("operating", "WarehouseProductRoll")
    Roll.objects.update(unit_cost_base=None)


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0078_warehouseproductroll_unit_cost_base"),
    ]

    operations = [
        migrations.RunPython(stamp_cost, blank_cost),
    ]
