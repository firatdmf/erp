"""Stock is always a catalog variant, so a warehouse row is born linked.

Every path that creates a row — a goods receipt, a roll scan, the Excel
import — used to write the row first and link it to the catalog after,
with a warning when the catalog could not take it. The row then sat on the
shelf as stock no catalog entry stood behind. Now the variant is found or
made first, and stock the catalog can't take is refused, not shelved.

Run with:
    python manage.py test operating.tests.test_stock_born_linked
"""
import io
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import Product, ProductVariant
from operating.catalog_sync import (CatalogSyncConflict, sync_roll_to_catalog,
                                    variant_for_new_row)
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


def a_warehouse():
    return Warehouse.objects.create(
        name="Fabrika", accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])


class SignedIn(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(
            username="stocker", password="pw", email="s@t.k"))
        self.warehouse = a_warehouse()


class TheVariantForANewRow(TestCase):
    def test_a_known_sku_is_that_variant_left_as_it_is(self):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="Grek", attributes=[("color", "white")], variant_sku="LZK000054")
        self.assertEqual(variant_for_new_row("lzk000054", "GREK BEYAZ").pk, variant.pk)
        self.assertEqual(ProductVariant.everywhere.count(), 1)

    def test_an_unknown_sku_is_made_under_the_product_it_derives(self):
        variant = variant_for_new_row("K12767.G28", "FLORENZA KREM")
        self.assertEqual(variant.variant_sku, "K12767.G28")
        self.assertTrue(variant.product_id)

    def test_no_sku_is_refused(self):
        with self.assertRaises(CatalogSyncConflict):
            variant_for_new_row("", "GREK")


class AGoodsReceipt(SignedIn):
    def setUp(self):
        super().setUp()
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.account = CurrentAccount.objects.create(
            book=self.warehouse.accounting_book, code="TST-KRV", name="Karven",
            type="supplier", default_currency=usd)

    def _receive(self, variant_sku, name="K24644"):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "current_account_id": self.account.pk, "unit": "m",
                "products": [{
                    "main_product": {"mode": "new", "name": name, "sku": name},
                    "has_variants": True,
                    "variants": [{"name": "G07", "sku": variant_sku, "price": "3.50",
                                  "currency": "USD", "tops": [{"qty": 30}]}],
                }],
            }),
            content_type="application/json")

    def test_its_new_row_is_born_linked_to_a_variant_of_the_same_sku(self):
        response = self._receive("K24644.G07")
        self.assertEqual(response.status_code, 200, response.content)
        row = WarehouseProduct.objects.get(sku="K24644.G07")
        self.assertEqual(row.catalog_variant.variant_sku, "K24644.G07")

    def test_a_sku_another_product_holds_is_refused_and_nothing_is_shelved(self):
        sync_roll_to_catalog(base_name="Florenza", attributes=[("color", "cream")],
                             variant_sku="K24644.G07")
        response = self._receive("K24644.G07", name="Something Else")
        self.assertEqual(response.status_code, 409, response.content)
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())


class ARollScan(SignedIn):
    def _scan(self, **fields):
        data = {"commit": "true", "quantity": "30", "barcode": "2000043130007",
                "reason": "opening"}
        data.update(fields)
        return self.client.post(
            reverse("operating:warehouse_roll_scan", args=[self.warehouse.pk]), data)

    def test_a_new_sku_is_shelved_already_linked(self):
        response = self._scan(sku="K24620.G33", name="GREK TÜL")
        self.assertEqual(response.status_code, 200, response.content)
        row = WarehouseProduct.objects.get(sku="K24620.G33")
        self.assertEqual(row.catalog_variant.variant_sku, "K24620.G33")
        self.assertTrue(response.json()["catalog"]["variant_created"])

    def test_a_known_sku_links_its_variant_and_leaves_it_as_it_is(self):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="Grek", attributes=[("color", "white")], variant_sku="LZK000054")
        response = self._scan(sku="LZK000054", name="GREK 7103 BEYAZ",
                              catalog_attribute="color", catalog_value="ecru")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(WarehouseProduct.objects.get(sku="LZK000054").catalog_variant_id,
                         variant.pk)
        self.assertEqual(ProductVariant.everywhere.count(), 1)

    def test_a_label_with_no_sku_is_refused_and_nothing_is_shelved(self):
        response = self._scan(sku="", name="GREK TÜL")
        self.assertEqual(response.status_code, 409, response.content)
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())


class TheExcelImport(SignedIn):
    def _import(self, *rows):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["Name", "Code", "Quantity", "Purchase Price", "Currency"])
        for row in rows:
            ws.append(row)
        upload = io.BytesIO()
        wb.save(upload)
        upload.seek(0)
        upload.name = "stock.xlsx"
        response = self.client.post(
            reverse("operating:warehouse_product_import", args=[self.warehouse.pk]),
            {"file": upload})
        return b"".join(response.streaming_content).decode()

    def test_a_new_row_is_born_linked(self):
        self._import(["GREK BEYAZ", "LZK000054", 10, 0.70, "USD"])
        row = WarehouseProduct.objects.get(sku="LZK000054")
        self.assertEqual(row.catalog_variant.variant_sku, "LZK000054")

    def test_one_sku_twice_in_a_sheet_is_one_row_and_says_so(self):
        body = self._import(["GREK BEYAZ", "LZK000054", 10, 0.70, "USD"],
                            ["GREK BEYAZ", "lzk000054", 5, 0.70, "USD"])
        self.assertEqual(WarehouseProduct.objects.count(), 1)
        self.assertIn("already on this shelf", body)
