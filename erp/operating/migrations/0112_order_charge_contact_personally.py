# Who an order is charged to when its contact is filed under a company.
# A column with a default only — no row is rewritten. The database keeps
# the default too, so the release still running while this one deploys can
# go on inserting orders that do not name the column.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0111_meter_code_m"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="charge_contact_personally",
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(
            "ALTER TABLE operating_order "
            "ALTER COLUMN charge_contact_personally SET DEFAULT false",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
