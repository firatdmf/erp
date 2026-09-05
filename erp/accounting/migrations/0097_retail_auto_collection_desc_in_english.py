"""Restate the historical retail auto-collection descriptions in English.

Nine Payments carry ``Perakende otomatik tahsilat — Sipariş #N``, written
by the automatic collection leg that completion used to run. That leg is
gone; the rows remain, and reverse_retail_order_financials still finds
them by description prefix when an order is un-shipped.

So the column and the constant have to move together. _RETAIL_AUTO_DESC is
now "Retail automatic collection", and this restates the rows to match —
translating the "Sipariş #N" tail as well, since half a sentence in each
language is worse than either.

Anchored on the exact Turkish prefix, so a description somebody typed by
hand cannot be caught by it.
"""
from django.db import migrations

TR_PREFIX = "Perakende otomatik tahsilat"
EN_PREFIX = "Retail automatic collection"

TR_ORDER = "Sipariş #"
EN_ORDER = "Order #"


def _restate(apps, old_prefix, new_prefix, old_order, new_order):
    Payment = apps.get_model("accounting", "Payment")
    for pay in Payment.objects.filter(description__startswith=old_prefix):
        pay.description = (pay.description
                           .replace(old_prefix, new_prefix, 1)
                           .replace(old_order, new_order, 1))
        pay.save(update_fields=["description"])


def to_english(apps, schema_editor):
    _restate(apps, TR_PREFIX, EN_PREFIX, TR_ORDER, EN_ORDER)


def back_to_turkish(apps, schema_editor):
    _restate(apps, EN_PREFIX, TR_PREFIX, EN_ORDER, TR_ORDER)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0096_retail_cari_named_in_english'),
    ]

    operations = [
        migrations.RunPython(to_english, back_to_turkish),
    ]
