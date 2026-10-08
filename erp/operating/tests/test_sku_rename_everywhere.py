"""A SKU is one variant on every shelf, so renaming it renames it everywhere.

Editing a warehouse product's SKU used to delete its catalog variant and
make a new one under the new SKU. That was sound while a variant stood in
one warehouse. Once the same SKU stood in two, the other warehouse's row
kept the old SKU and lost its catalog link, the variant's attributes and
files went with it, and a variant with an order line could not be deleted
at all — the row was left renamed beside a variant that was not.

Now the variant is renamed in place and every other warehouse row that
carried the old SKU takes the new one.

Run with:
    python manage.py test operating.tests.test_sku_rename_everywhere
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductVariant
from operating.catalog_sync import (resync_warehouse_product, sync_roll_to_catalog,
                                    variant_attributes)
from operating.models import Warehouse, WarehouseProduct


class RenamingASkuTest(TestCase):
    def setUp(self):
        book = Book.objects.get_or_create(name="Laleli Fabric")[0]
        self.shop = Warehouse.objects.create(name="Laleli", accounting_book=book)
        self.factory = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=book)
        self.product, self.variant, _pc, _vc = sync_roll_to_catalog(
            base_name="Sable", attributes=[("color", "ecru")], variant_sku="LZK0000120")
        self.here = self._row(self.shop, "LZK0000120")
        self.there = self._row(self.factory, "LZK0000120")

    def _row(self, warehouse, sku):
        return WarehouseProduct.objects.create(
            warehouse=warehouse, name="SABLE EKRU", sku=sku, quantity=0,
            catalog_variant=self.variant)

    def _rename(self, sku):
        self.here.sku = sku
        self.here.save(update_fields=["sku"])
        return resync_warehouse_product(self.here)

    def test_the_variant_is_renamed_not_replaced(self):
        variant, warning = self._rename("SBL-ECRU")
        self.assertIsNone(warning)
        self.assertEqual(variant.pk, self.variant.pk)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.variant_sku, "SBL-ECRU")
        self.assertEqual(self.variant.product_id, self.product.pk)
        self.assertEqual(variant_attributes(self.variant), [("color", "ecru")])
        self.assertEqual(ProductVariant.everywhere.count(), 1)

    def test_the_other_warehouse_takes_the_new_sku_and_keeps_its_link(self):
        self._rename("SBL-ECRU")
        self.there.refresh_from_db()
        self.assertEqual(self.there.sku, "SBL-ECRU")
        self.assertEqual(self.there.catalog_variant_id, self.variant.pk)
        self.here.refresh_from_db()
        self.assertEqual(self.here.catalog_variant_id, self.variant.pk)

    def test_a_row_spelled_another_way_is_left_alone(self):
        odd = self._row(self.shop, "3002")
        self._rename("SBL-ECRU")
        odd.refresh_from_db()
        self.assertEqual(odd.sku, "3002")
        self.assertEqual(odd.catalog_variant_id, self.variant.pk)

    def test_a_sku_another_variant_holds_is_refused_and_nothing_follows(self):
        sync_roll_to_catalog(base_name="Sable", attributes=[("color", "white")],
                             variant_sku="SBL-WHITE")
        variant, warning = self._rename("SBL-WHITE")
        self.assertIsNone(variant)
        self.assertTrue(warning)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.variant_sku, "LZK0000120")
        self.there.refresh_from_db()
        self.assertEqual(self.there.sku, "LZK0000120")

    def test_a_base_code_in_the_new_sku_moves_the_variant(self):
        florenza = Product.objects.create(title="Florenza", sku="K12767", featured=True)
        variant, _warning = self._rename("K12767.G28")
        self.assertEqual(variant.pk, self.variant.pk)
        self.assertEqual(variant.product_id, florenza.pk)
        # Sable was hidden and is now empty.
        self.assertFalse(Product.everywhere.filter(pk=self.product.pk).exists())

    def test_the_edit_form_renames_both_warehouses(self):
        user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(user)
        response = self.client.post(
            reverse("operating:warehouse_product_edit", args=[self.shop.pk, self.here.pk]),
            {"name": "SABLE EKRU", "sku": "SBL-ECRU"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["catalog_warning"])
        self.there.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual((self.there.sku, self.variant.variant_sku), ("SBL-ECRU", "SBL-ECRU"))
