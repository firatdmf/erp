from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0102_newsletter_clear_placeholder_phones"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="newslettersubscription",
            constraint=models.CheckConstraint(
                check=models.Q(("email__isnull", False), ("phone__isnull", False), _connector="OR"),
                name="marketing_newsletter_needs_a_contact"),
        ),
    ]
