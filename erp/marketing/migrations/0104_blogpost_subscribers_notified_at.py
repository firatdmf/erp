from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0103_newsletter_needs_a_contact"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="subscribers_notified_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
