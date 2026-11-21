from django.db import migrations


class Migration(migrations.Migration):
    """Copy every order's order_status into the status column beside it
    (0133). New writes are copied by the trigger already."""

    dependencies = [
        ("operating", "0133_order_status_column_beside"),
    ]

    operations = [
        migrations.RunSQL(
            "UPDATE operating_order SET status = order_status "
            "WHERE status IS DISTINCT FROM order_status",
            migrations.RunSQL.noop,
        ),
    ]
