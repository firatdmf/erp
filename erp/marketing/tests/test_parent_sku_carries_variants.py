"""Renaming a product's SKU renames the variant SKUs built on it.

A variant SKU is PARENT.VALUES (S-ORKIDE-15.BEIGE-300-275), and the
warehouse rows copy the variant's. The create page carried the variants
along as the parent was typed, but an edit did not: S-ORKIDE-15 became
S-ORKIDE while its variant and shelf still read S-ORKIDE-15.… Now the
product's save carries them, whoever saves it.

Run with:
    python manage.py test marketing.tests.test_parent_sku_carries_variants
"""
from decimal import Decimal

from django.test import TestCase

from accounting.models import Book
from marketing.models import Product, ProductVariant
from operating.models import Warehouse, WarehouseProduct


class ParentSkuCarriesVariantsTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="S-ORKIDE-15", sku="S-ORKIDE-15")
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="S-ORKIDE-15.BEIGE-300-275")
        shelf = Warehouse.objects.create(
            name="Laleli", accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.row = WarehouseProduct.objects.create(
            warehouse=shelf, name="S-ORKIDE-15*275 LT-8024-BEIGE 300", sku=self.variant.variant_sku,
            quantity=Decimal("0"), catalog_variant=self.variant)

    def _rename(self, sku):
        self.product.sku = sku
        self.product.save()
        self.variant.refresh_from_db()
        self.row.refresh_from_db()

    def test_the_variant_and_its_shelf_follow_the_parent(self):
        self._rename("S-ORKIDE")
        self.assertEqual(self.variant.variant_sku, "S-ORKIDE.BEIGE-300-275")
        self.assertEqual(self.row.sku, "S-ORKIDE.BEIGE-300-275")

    def test_a_variant_spelled_another_way_is_left_alone(self):
        odd = ProductVariant.objects.create(product=self.product, variant_sku="MT-1004-white")
        self._rename("S-ORKIDE")
        odd.refresh_from_db()
        self.assertEqual(odd.variant_sku, "MT-1004-white")

    def test_a_new_sku_already_taken_is_not_forced(self):
        other = Product.objects.create(title="other", sku="OTHER")
        ProductVariant.objects.create(product=other, variant_sku="S-ORKIDE.BEIGE-300-275")
        self._rename("S-ORKIDE")
        self.assertEqual(self.variant.variant_sku, "S-ORKIDE-15.BEIGE-300-275")

    def test_saving_other_fields_renames_nothing(self):
        self.product.title = "Orkide"
        self.product.save(update_fields=["title"])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.variant_sku, "S-ORKIDE-15.BEIGE-300-275")
