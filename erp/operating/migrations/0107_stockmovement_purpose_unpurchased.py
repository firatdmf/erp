from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0106_stockmovement_purpose_loss"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="purpose",
            field=models.CharField(blank=True, choices=[("", "—"), ("sample", "Sample for a client"),
                                                        ("display", "Display — showroom or trade show"),
                                                        ("loss", "Lost, damaged or defective"),
                                                        ("correction", "Re-measured"),
                                                        ("opening", "Opening stock"),
                                                        ("found", "Found after the stock was recorded")],
                                   default="", max_length=16),
        ),
    ]
