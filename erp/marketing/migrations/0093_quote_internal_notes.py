from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0092_quote_item_rolls"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="internal_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
