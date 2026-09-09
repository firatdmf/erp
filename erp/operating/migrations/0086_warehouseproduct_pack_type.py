"""Say how a product is PACKED, separately from what it is counted in.

`unit` answers "how much is there" — metres, pieces, packs, kilos.
`pack_type` answers "what is one stock item" — a roll, a box, a bale.

They were one field, with the pack derived from the unit: metres meant a
roll, packs meant a box. That mapping is right often enough to be
tempting and wrong often enough to matter — metres arrive on a bolt as
readily as a roll, and pieces come in a bag as readily as a box. Two
facts, so two fields.

Existing rows are seeded from their unit, which is exactly what the
derived version already said, so nothing on any screen changes on the
day this runs. Every product in the warehouse today is either fabric on
rolls or ready-made curtains in boxes, and both come out right.
"""
from django.db import migrations, models


def seed_pack_from_unit(apps, schema_editor):
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    for unit, pack in (("mt", "roll"), ("kg", "bale"),
                       ("adet", "box"), ("paket", "box")):
        WarehouseProduct.objects.filter(unit=unit).update(pack_type=pack)


def back_to_the_default(apps, schema_editor):
    """The reverse cannot recover what somebody set by hand — the whole
    point of the field is that it stops being a function of the unit. It
    puts every row back to the model default so the column can be dropped
    without leaving a half-state behind."""
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    WarehouseProduct.objects.update(pack_type="roll")


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0085_order_number_sequence"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouseproduct",
            name="pack_type",
            field=models.CharField(
                choices=[("roll", "Roll"), ("box", "Box"), ("bale", "Bale"),
                         ("bag", "Bag"), ("bundle", "Bundle"),
                         ("pallet", "Pallet")],
                default="roll", max_length=12,
                help_text="What one stock item of this product physically is",
            ),
        ),
        migrations.RunPython(seed_pack_from_unit, back_to_the_default),
    ]
