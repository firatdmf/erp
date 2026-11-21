from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 2 of 3: Order.status reads and writes the status column (0133)
    instead of order_status. No table change: the trigger keeps both
    columns equal while the previous release still writes order_status.
    Step 3 drops the trigger and order_status."""

    dependencies = [
        ("operating", "0134_order_status_column_filled"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="order",
                    name="status",
                    field=models.CharField(
                        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('packaging', 'Packaging'), ('shipped', 'Shipped'), ('in_transit', 'In Transit'), ('out_for_delivery', 'Out for Delivery'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled'), ('returned', 'Returned')],
                        default="pending",
                        help_text="The order status shown to the customer",
                        max_length=32,
                    ),
                ),
            ],
        ),
    ]
