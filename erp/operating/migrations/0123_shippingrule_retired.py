# Shipping rules per destination country gave way to each warehouse's own
# shipping reach (0122). State only: the old release, still serving while
# this one deploys, reads the table, so it is dropped in a later release.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0122_warehouse_shipping_reach'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name='ShippingRule')],
            database_operations=[],
        ),
    ]
