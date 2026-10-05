from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0102_english_field_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="purpose",
            field=models.CharField(blank=True, choices=[("", "—"), ("sample", "Sample for a client"),
                                                        ("display", "Display — showroom or trade show"),
                                                        ("correction", "Lost, damaged or re-measured")],
                                   default="", max_length=16),
        ),
    ]
