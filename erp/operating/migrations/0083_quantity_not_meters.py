"""Stop calling every quantity in the warehouse "meters".

The stock columns were named when the warehouse held nothing but fabric.
The arithmetic was always generic — a number of somethings — but the names
were not, so a box of 20 ready-made curtain sets had to be stored in a
column called `meters` and rendered on screen as "20m".

RenameField, not add-and-drop: these columns hold 100,888 metres of real
fabric across 4,600 stock items, and Postgres renames a column in place
without touching a row.

`unit` says what the numbers mean, from the vocabulary the goods-receipt
form has offered all along (mt / adet / paket / kg). It defaults to metres
because every product that exists when this runs is fabric — that is a
fact about the data, not a guess.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0082_order_current_account"),
    ]

    operations = [
        migrations.RenameField(
            model_name="warehouseproductitem",
            old_name="meters",
            new_name="quantity",
        ),
        migrations.RenameField(
            model_name="warehouseproductitem",
            old_name="meters_remaining",
            new_name="quantity_remaining",
        ),
        migrations.RenameField(
            model_name="orderstockreservation",
            old_name="meters",
            new_name="quantity",
        ),
        migrations.AddField(
            model_name="warehouseproduct",
            name="unit",
            field=models.CharField(
                choices=[("mt", "Metre"), ("adet", "Adet"),
                         ("paket", "Paket"), ("kg", "Kilogram")],
                default="mt", max_length=8,
                help_text="What this product is counted in",
            ),
        ),
        migrations.AlterField(
            model_name="warehouseproductitem",
            name="quantity",
            field=models.DecimalField(
                decimal_places=2, max_digits=10,
                help_text="How much arrived, in the product's unit of measure",
            ),
        ),
        migrations.AlterField(
            model_name="warehouseproductitem",
            name="quantity_remaining",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                help_text="How much is left (drops as stock-outs happen)",
            ),
        ),
        migrations.AlterField(
            model_name="orderstockreservation",
            name="quantity",
            field=models.DecimalField(
                decimal_places=2, max_digits=10,
                help_text="How much is held for the order, in the product's unit.",
            ),
        ),
    ]
