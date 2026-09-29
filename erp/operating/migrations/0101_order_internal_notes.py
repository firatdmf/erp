from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0100_stockmovement_purpose"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="internal_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
