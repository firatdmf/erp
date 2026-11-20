from django.db import migrations, models


class Migration(migrations.Migration):
    """Order.order_status becomes Order.status; the retired rollup that held
    the name leaves the model. No table change beyond letting the old
    column go empty: the new name keeps the order_status column
    (db_column), and the old status column is dropped in a later release,
    once no running code selects it."""

    dependencies = [
        ("operating", "0127_drop_procurement"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE operating_order ALTER COLUMN status DROP NOT NULL",
                    "ALTER TABLE operating_order ALTER COLUMN status SET NOT NULL",
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name="order", name="status"),
                migrations.RenameField(model_name="order", old_name="order_status", new_name="status"),
                migrations.AlterField(
                    model_name="order",
                    name="status",
                    field=models.CharField(
                        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('packaging', 'Packaging'), ('shipped', 'Shipped'), ('in_transit', 'In Transit'), ('out_for_delivery', 'Out for Delivery'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled'), ('returned', 'Returned')],
                        db_column="order_status",
                        default="pending",
                        help_text="The order status shown to the customer",
                        max_length=32,
                    ),
                ),
            ],
        ),
    ]
