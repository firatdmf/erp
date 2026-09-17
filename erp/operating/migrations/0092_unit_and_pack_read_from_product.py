from django.db import migrations, models


def copy_back_from_product(apps, schema_editor):
    """Reversing: the rows' own columns were not kept up to date while the
    product owned the facts, so refill them from it."""
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    rows = list(WarehouseProduct.objects
                .filter(catalog_variant__isnull=False)
                .select_related("catalog_variant__product"))
    for wp in rows:
        wp.unit = wp.catalog_variant.product.unit
        wp.pack_type = wp.catalog_variant.product.pack_type
    WarehouseProduct.objects.bulk_update(rows, ["unit", "pack_type"], batch_size=500)


class Migration(migrations.Migration):
    """WarehouseProduct.unit / pack_type now come from the main product.

    The fields leave the model, but the columns stay for one release: the
    previous deploy is still serving while this one migrates, and it reads
    and writes them. They get database defaults so this release's inserts,
    which no longer name them, still satisfy NOT NULL. A later migration
    drops them.
    """

    dependencies = [
        ('operating', '0091_warehouse_costs_not_negative'),
        ('marketing', '0086_product_owns_unit_and_pack'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, copy_back_from_product),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='warehouseproduct', name='pack_type'),
                migrations.RemoveField(model_name='warehouseproduct', name='unit'),
            ],
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE operating_warehouseproduct "
                    "ALTER COLUMN unit SET DEFAULT 'mt', "
                    "ALTER COLUMN pack_type SET DEFAULT 'roll'",
                    "ALTER TABLE operating_warehouseproduct "
                    "ALTER COLUMN unit DROP DEFAULT, "
                    "ALTER COLUMN pack_type DROP DEFAULT",
                ),
            ],
        ),
    ]
