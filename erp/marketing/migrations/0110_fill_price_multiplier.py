# Data only (see 0109 for the columns). Prices are worked out from cost ×
# a multiplier from now on (marketing/pricing.py, 2026-10-15). Each group's
# and product's percentage margin becomes the multiplier it meant:
# 200% → 3, 30% → 1.3. A group with no margin took the one-third default
# (C24 cleared fabric's 30% on purpose), so it gets 4/3.

from decimal import Decimal

from django.db import migrations


def _as_multiplier(margin):
    value = Decimal("1") + Decimal(margin) / Decimal("100")
    text = format(value.normalize(), "f")
    return text


def forwards(apps, schema_editor):
    ProductCategory = apps.get_model("marketing", "ProductCategory")
    Product = apps.get_model("marketing", "Product")
    for group in ProductCategory.objects.filter(price_multiplier=""):
        group.price_multiplier = ("4/3" if group.profit_margin is None
                                  else _as_multiplier(group.profit_margin))
        group.save(update_fields=["price_multiplier"])
    for product in Product.objects.filter(price_multiplier="", profit_margin__isnull=False):
        product.price_multiplier = _as_multiplier(product.profit_margin)
        product.save(update_fields=["price_multiplier"])


def backwards(apps, schema_editor):
    apps.get_model("marketing", "ProductCategory").objects.update(price_multiplier="")
    apps.get_model("marketing", "Product").objects.update(price_multiplier="")


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0109_price_multiplier'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
