from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0099_carrier_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="purpose",
            field=models.CharField(blank=True, choices=[("", "—"), ("sample", "Sample for a client")],
                                   default="", max_length=16),
        ),
    ]
