from django.db import migrations


class Migration(migrations.Migration):
    """Drop the retired production rollup's column. It left the model in
    0128 (Order.status is the old order_status, kept in the order_status
    column); since then nothing reads or writes operating_order.status."""

    dependencies = [
        ("operating", "0131_warehouseproductitem_charges_per_unit"),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE operating_order DROP COLUMN IF EXISTS status",
            "ALTER TABLE operating_order ADD COLUMN status varchar(32) NULL",
        ),
    ]
