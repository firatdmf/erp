from django.db import migrations


class Migration(migrations.Migration):
    """Step 3 of 3: the status column stands alone. Since 0135 nothing
    reads order_status; the trigger that kept it equal and the column go,
    and status becomes required, as order_status was."""

    dependencies = [
        ("operating", "0135_order_status_reads_its_column"),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS operating_order_status_sync ON operating_order;
            DROP FUNCTION IF EXISTS operating_order_status_sync();
            ALTER TABLE operating_order ALTER COLUMN status SET NOT NULL;
            ALTER TABLE operating_order DROP COLUMN order_status;
            """,
            """
            ALTER TABLE operating_order ADD COLUMN order_status varchar(32) NULL;
            UPDATE operating_order SET order_status = status;
            ALTER TABLE operating_order ALTER COLUMN order_status SET NOT NULL;
            ALTER TABLE operating_order ALTER COLUMN status DROP NOT NULL;
            """,
        ),
    ]
