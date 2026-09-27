from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0109_movement_type_fx_adjustment"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="published_rate",
            field=models.DecimalField(
                blank=True, decimal_places=8,
                help_text="The published rate for the date, kept beside a typed one.",
                max_digits=16, null=True),
        ),
    ]
