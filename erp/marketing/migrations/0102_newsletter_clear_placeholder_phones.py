from django.db import migrations
from django.db.models import Q


def clear_placeholders(apps, schema_editor):
    """Email-only sign-ups were stored under a made-up phone — first one
    shared "0000000000", then a "no-phone-…" each. They have no phone."""
    Subscription = apps.get_model("marketing", "NewsletterSubscription")
    Subscription.objects.filter(
        Q(phone="0000000000") | Q(phone__startswith="no-phone-"), email__isnull=False,
    ).update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0101_newsletter_email_or_phone"),
    ]

    operations = [
        migrations.RunPython(clear_placeholders, migrations.RunPython.noop),
    ]
