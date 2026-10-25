"""Product.tracking: whether each stock item has a label of its own, or the
barcode names the variant. It used to be read off the unit (piece and pack
were sold by count); it is now said on the product, and filled from the
unit once so nothing changed on the day it arrived."""
import importlib

from django.apps import apps
from django.test import TestCase

from marketing import units
from marketing.forms import ProductForm
from marketing.models import Product

fill = importlib.import_module("marketing.migrations.0117_fill_product_tracking").fill


class ProductTracking(TestCase):
    def test_a_new_product_is_tracked_item_by_item(self):
        product = Product.objects.create(title="Krep", featured=False)
        self.assertEqual(product.tracking, "item")
        self.assertFalse(product.sold_by_count)

    def test_the_fill_follows_what_the_unit_used_to_decide(self):
        made = {unit: Product.objects.create(title=unit, featured=False, unit=unit)
                for unit, _label in units.UNIT_CHOICES}
        fill(apps, None)
        tracking = dict(Product.objects.filter(pk__in=[p.pk for p in made.values()])
                        .values_list("unit", "tracking"))
        self.assertEqual(tracking, {"m": "item", "kg": "item",
                                    "piece": "variant", "pack": "variant"})

    def test_set_unit_changes_the_tracking_alone(self):
        product = Product.objects.create(title="Duvet", featured=False, unit="piece")
        self.assertTrue(product.set_unit(tracking="variant"))
        product.refresh_from_db()
        self.assertEqual((product.unit, product.tracking), ("piece", "variant"))
        self.assertFalse(product.set_unit(tracking="variant"))

    def test_the_product_form_offers_it(self):
        field = ProductForm().fields["tracking"]
        self.assertEqual([value for value, _label in field.choices if value],
                         ["item", "variant"])
