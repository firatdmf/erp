# Hand-written: the only change is the field's default, which lives in
# Django, not in the database — so this alters no column, it records that
# a new account no longer starts in "TR". Existing rows keep their value.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0111_purchase_change"),
    ]

    operations = [
        migrations.AlterField(
            model_name="currentaccount",
            name="billing_country",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
