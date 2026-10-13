from django.db import migrations
from django.utils import timezone


def mark_published(apps, schema_editor):
    """Posts already on the website are old news: stamp them, so that
    unpublishing and republishing one does not write to the whole list."""
    BlogPost = apps.get_model("marketing", "BlogPost")
    BlogPost.objects.filter(
        is_published=True, subscribers_notified_at__isnull=True,
    ).update(subscribers_notified_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0104_blogpost_subscribers_notified_at"),
    ]

    operations = [
        migrations.RunPython(mark_published, migrations.RunPython.noop),
    ]
