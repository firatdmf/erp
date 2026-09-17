"""A new product's SKUs read PARENT.VALUE-VALUE (K24644.BEYAZ-140).

The product SKU carries no dot and is stored in capitals; each variant SKU
is that SKU, a dot, and a non-empty suffix in capitals. Only products being
created are held to it — existing products, and the warehouse items linked
to them, keep the SKUs they already have.

Run with:
    python manage.py test marketing.tests.test_new_product_sku_rule
"""
import json

from django.test import TestCase

from marketing.forms import ProductForm, _skus_off_the_parent
from marketing.models import Product


def _variants(*skus):
    return json.dumps({"product_variant_list": [{"variant_sku": s} for s in skus]})


class TheVariantSkusMustHangOffTheParent(TestCase):
    def test_parent_dot_suffix_in_capitals_passes(self):
        self.assertEqual(
            _skus_off_the_parent(_variants("K24644.BEYAZ-140", "K24644.AÇIK_MAVİ-140"), "K24644"),
            set())

    def test_anything_else_is_named(self):
        off = _skus_off_the_parent(
            _variants("K24644.beyaz-140", "K24644.", "K24644_BEYAZ", "BEYAZ-140", ""), "K24644")
        self.assertEqual(off, {"K24644.beyaz-140", "K24644.", "K24644_BEYAZ", "BEYAZ-140", "?"})

    def test_a_longer_parent_sharing_the_prefix_does_not_pass(self):
        self.assertEqual(_skus_off_the_parent(_variants("K246440.BEYAZ"), "K24644"),
                         {"K246440.BEYAZ"})


class TheRuleAppliesOnlyWhenCreating(TestCase):
    def _errors(self, data, is_update=False, instance=None):
        form = ProductForm(data=data, is_update=is_update, instance=instance)
        form.is_valid()
        return form

    def test_a_new_product_sku_is_stored_in_capitals(self):
        form = self._errors({"title": "Krep", "sku": "  k24644 "})
        self.assertNotIn("sku", form.errors)
        self.assertEqual(form.cleaned_data["sku"], "K24644")

    def test_a_new_product_sku_with_a_dot_is_refused(self):
        form = self._errors({"title": "Krep", "sku": "K24644.G07"})
        self.assertIn("sku", form.errors)

    def test_a_new_product_with_an_off_rule_variant_is_refused(self):
        form = self._errors({"title": "Krep", "sku": "K24644",
                             "variants_json": _variants("K24644.BEYAZ", "beyaz")})
        self.assertIn("beyaz", " ".join(form.non_field_errors()))

    def test_a_new_product_with_on_rule_variants_raises_no_sku_error(self):
        form = self._errors({"title": "Krep", "sku": "k24644",
                             "variants_json": _variants("K24644.BEYAZ-140")})
        self.assertNotIn("sku", form.errors)
        self.assertFalse(form.non_field_errors())

    def test_editing_an_existing_product_keeps_its_skus_as_they_are(self):
        product = Product.objects.create(title="Old", sku="N1718T.G56")
        form = self._errors({"title": "Old", "sku": "N1718T.G56",
                             "variants_json": _variants("cappucino")},
                            is_update=True, instance=product)
        self.assertNotIn("sku", form.errors)
        self.assertFalse(form.non_field_errors())
        self.assertEqual(form.cleaned_data["sku"], "N1718T.G56")


class TheFormAsksUnitAndPackNotTheStorefrontUnit(TestCase):
    """The storefront unit is derived from the unit on save, so the form
    offers what a person decides and never the copy."""

    def test_fields(self):
        form = ProductForm()
        self.assertIn("unit", form.fields)
        self.assertIn("pack_type", form.fields)
        self.assertNotIn("unit_of_measurement", form.fields)
