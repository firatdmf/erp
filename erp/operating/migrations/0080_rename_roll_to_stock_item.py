"""Rolls become stock items.

WarehouseProductRoll named the only thing the warehouse has ever held.
Fabric arrives on rolls, but nothing about a warehouse requires that, and
a model called Roll cannot hold a box of buttons without lying about it.
The rename says what the row is — one physical unit of stock — and leaves
room for units that are not wound on a core.

Everything here is a rename: the tables keep every row, the columns keep
every value, and the foreign keys keep pointing where they pointed.
`meters` and `meters_remaining` are deliberately NOT touched — those are
the genuinely fabric-shaped part, and generalising them to a quantity plus
a unit of measure is a real design change rather than a rename. Better
done when the first non-fabric product actually arrives and can say what
it needs.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0079_backfill_roll_unit_cost_base"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="WarehouseProductRoll", new_name="WarehouseProductItem"),
        migrations.RenameModel(
            old_name="OrderRollReservation", new_name="OrderStockReservation"),
        migrations.RenameField(
            model_name="stockmovement", old_name="roll", new_name="stock_item"),
        migrations.RenameField(
            model_name="orderstockreservation", old_name="roll",
            new_name="stock_item"),
    ]
