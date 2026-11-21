"""Tick the filters the storefront showed before the groups chose them.

Until now the storefront filtered every listing by color, header and any
"size…" attribute its products carried. Every group already lists exactly
the ones its website products use, so ticking those keeps each listing's
filters as they were. Its own file: data, not schema."""
from django.db import migrations


def tick(apps, schema_editor):
    Preset = apps.get_model("marketing", "CategoryVariantAttribute")
    for preset in Preset.objects.select_related("attribute"):
        name = preset.attribute.name
        if name in ("color", "header") or "size" in name:
            preset.storefront_filter = True
            preset.save(update_fields=["storefront_filter"])


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0121_categoryvariantattribute_storefront_filter'),
    ]

    operations = [
        migrations.RunPython(tick, migrations.RunPython.noop),
    ]
