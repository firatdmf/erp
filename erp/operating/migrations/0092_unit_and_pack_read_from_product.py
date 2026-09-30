from django.db import migrations


def copy_back_from_product(apps, schema_editor):
    """Reversing: the rows' own columns were not kept up to date while the
    product owned the facts, so refill them from it.

    SQL rather than the historical models: reversing to before marketing
    0086 hands this a Product state without unit and pack_type, but with
    the "type" field whose column 0087 has already dropped."""
    schema_editor.execute(
        "UPDATE operating_warehouseproduct wp "
        "SET unit = p.unit, pack_type = p.pack_type "
        "FROM marketing_productvariant v "
        "JOIN marketing_product p ON p.id = v.product_id "
        "WHERE wp.catalog_variant_id = v.id")


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
