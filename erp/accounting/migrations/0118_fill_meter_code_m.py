"""Meters are coded "m", not "mt" (see marketing 0112). Invoice lines carry
the unit as free text; this rewrites the ones that say "mt"."""
from django.db import migrations


def mt_to_m(apps, schema_editor):
    apps.get_model("accounting", "InvoiceItem").objects.filter(unit="mt").update(unit="m")


def m_to_mt(apps, schema_editor):
    apps.get_model("accounting", "InvoiceItem").objects.filter(unit="m").update(unit="mt")


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0117_stock_transfer"),
        ("marketing", "0112_fill_meter_code_m"),
    ]

    operations = [
        migrations.RunPython(mt_to_m, m_to_mt),
    ]
