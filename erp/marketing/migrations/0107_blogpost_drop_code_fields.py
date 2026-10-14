from django.db import migrations


class Migration(migrations.Migration):
    """A blog post no longer carries HTML or scripts of its own for the
    website to run; the form and the post API stopped using these columns
    in d9517837, and their contents were cleared (blog cleanup B1)."""

    dependencies = [
        ("marketing", "0106_catalogwording"),
    ]

    operations = [
        migrations.RemoveField(model_name="blogpost", name="header_content"),
        migrations.RemoveField(model_name="blogpost", name="footer_content"),
    ]
