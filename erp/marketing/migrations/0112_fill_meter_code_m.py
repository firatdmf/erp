"""Meters are coded "m", not "mt" (Muhammed, 2026-10-18): the stored code
reads as the unit people write. Data only — 0111 changed the choices, and
quote lines carry the unit as free text with no choices at all."""
from django.db import migrations


def mt_to_m(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    QuoteItem = apps.get_model("marketing", "QuoteItem")
    Product.objects.filter(unit="mt").update(unit="m")
    Product.objects.filter(unit_of_measurement="mt").update(unit_of_measurement="m")
    QuoteItem.objects.filter(unit="mt").update(unit="m")


def m_to_mt(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    QuoteItem = apps.get_model("marketing", "QuoteItem")
    Product.objects.filter(unit="m").update(unit="mt")
    Product.objects.filter(unit_of_measurement="m").update(unit_of_measurement="mt")
    QuoteItem.objects.filter(unit="m").update(unit="mt")


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0111_meter_code_m"),
    ]

    operations = [
        migrations.RunPython(mt_to_m, m_to_mt),
    ]
