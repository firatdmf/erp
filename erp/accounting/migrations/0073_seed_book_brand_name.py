"""Give every existing book the brand's customer-facing name.

New books start blank and fall through to settings.BRAND_DISPLAY_NAME,
but the books already in the database predate the field, and the point
of putting the name on the book is that it is editable per book. Seeding
them means the field shows the real name when someone opens it, rather
than an empty box that only *behaves* as if it held one.

Read from settings rather than hardcoded so each brand's schema seeds
its own name.
"""
from django.conf import settings
from django.db import migrations


def seed(apps, schema_editor):
    Book = apps.get_model("accounting", "Book")
    name = (getattr(settings, "BRAND_DISPLAY_NAME", "")
            or getattr(settings, "BRAND_NAME", "")).strip()
    if not name:
        return
    Book.objects.filter(brand_name="").update(brand_name=name)


def unseed(apps, schema_editor):
    """Reversible: clearing the column returns every book to the
    settings default, which is what it printed before this ran."""
    Book = apps.get_model("accounting", "Book")
    Book.objects.update(brand_name="")


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0072_book_brand_name"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
