from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0105_sample_package"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="purpose",
            field=models.CharField(blank=True, choices=[("", "—"), ("sample", "Sample for a client"),
                                                        ("display", "Display — showroom or trade show"),
                                                        ("loss", "Lost, damaged or defective"),
                                                        ("correction", "Re-measured")],
                                   default="", max_length=16),
        ),
    ]
