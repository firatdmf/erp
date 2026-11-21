"""Each roll's share of its purchase's charges (accounting.purchase_charges).

Every roll so far carries none, so the column starts at 0 and keeps 0 as
its database default: the code still running while this deploys inserts
rolls without naming it."""

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0130_sell_down_goals'),
    ]

    operations = [
        migrations.AddField(
            model_name='warehouseproductitem',
            name='charges_per_unit',
            field=models.DecimalField(decimal_places=4, default=Decimal('0'), help_text="Part of unit_cost_base that is the purchase's charges", max_digits=14),
        ),
        migrations.RunSQL(
            "ALTER TABLE operating_warehouseproductitem ALTER COLUMN charges_per_unit SET DEFAULT 0;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
