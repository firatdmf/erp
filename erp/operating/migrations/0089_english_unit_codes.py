"""Store the unit in English too.

The labels were translated a while back but the CODES were not: the
column held "adet" and "paket", because that is what the goods-receipt
form had always submitted. So the stored value, the form option and
every lookup key that read them were Turkish.

Turkish belongs in the .po catalogue, where it can be translated, not in
the data, where it cannot. 45 rows carry "paket" today and none carries
"adet", but both are converted so a row written between this being
authored and being deployed is not stranded.

Reversible: the same mapping backwards, so the column can go back to
what the old code expects if this has to be rolled back.
"""
from django.db import migrations, models

RENAMES = [("paket", "pack"), ("adet", "piece")]


def to_english(apps, schema_editor):
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    for old, new in RENAMES:
        WarehouseProduct.objects.filter(unit=old).update(unit=new)


def back_to_turkish(apps, schema_editor):
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    for old, new in RENAMES:
        WarehouseProduct.objects.filter(unit=new).update(unit=old)


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0088_annual_number_reset"),
    ]

    operations = [
        migrations.RunPython(to_english, back_to_turkish),
        migrations.AlterField(
            model_name="warehouseproduct",
            name="unit",
            field=models.CharField(
                choices=[("mt", "Metre"), ("piece", "Piece"),
                         ("pack", "Pack"), ("kg", "Kilogram")],
                default="mt", max_length=8,
                help_text="What this product is counted in",
            ),
        ),
    ]
