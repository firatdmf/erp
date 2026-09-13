"""A warehouse cost is never below zero.

WarehouseProduct.purchase_price / cost_usd / cost_try and the per-item
WarehouseProductItem.unit_cost_base took any number. Production had none
negative (checked 2026-09-12: 0 of 2119 products, 0 of 8575 stock items),
so this is a guard, not a cleanup.

Same two layers as the catalogue (marketing.tests.test_non_negative_prices):
a validator per field, and a CHECK constraint per column for the bulk
import and intake paths that never call full_clean(). Every way a cost
gets typed in now refuses a negative one out loud before writing:

* goods receipt and purchase edit — used to drop it silently: a `price > 0`
  guard turned -12 into "no price" and the receipt went through unvalued;
* the Excel stock import — wrote it straight in; now a row error;
* the product edit modal and the roll scan — wrote it straight in;
* import_readymade_stock — wrote it straight in; now stops on the sheet row.

Run with:
    python manage.py test operating.test_warehouse_costs_not_negative
"""
import io
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounting.tests import test_received_purchase_edit as received
from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import Product
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


def a_warehouse():
    return Warehouse.objects.create(
        name="Fabrika", accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])


class TheColumnsRefuseANegativeCost(TestCase):
    def setUp(self):
        self.wp = WarehouseProduct.objects.create(
            warehouse=a_warehouse(), name="K24644 G07", sku="K24644.G07", quantity=0)

    def test_each_cost_fails_validation_on_its_own_field(self):
        for field in ("purchase_price", "cost_usd", "cost_try"):
            setattr(self.wp, field, Decimal("-1"))
            with self.assertRaises(ValidationError) as caught:
                self.wp.full_clean()
            self.assertIn(field, caught.exception.message_dict)
            setattr(self.wp, field, None)

    def test_the_database_refuses_it_without_full_clean(self):
        for field in ("purchase_price", "cost_usd", "cost_try"):
            setattr(self.wp, field, Decimal("-1"))
            with self.assertRaises(IntegrityError), transaction.atomic():
                WarehouseProduct.objects.bulk_update([self.wp], [field])
            setattr(self.wp, field, None)

    def test_a_stock_item_cannot_be_stamped_below_zero_either(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WarehouseProductItem.objects.create(
                product=self.wp, quantity=10, quantity_remaining=10,
                unit_cost_base=Decimal("-3.5"))

    def test_zero_and_blank_are_still_fine(self):
        self.wp.purchase_price = self.wp.cost_usd = self.wp.cost_try = Decimal("0")
        self.wp.save()
        WarehouseProductItem.objects.create(
            product=self.wp, quantity=1, quantity_remaining=1, unit_cost_base=None)


class AGoodsReceiptWithANegativePriceIsRefused(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username="receiver", password="pw", email="r@e.c")
        self.client.force_login(user)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.account = CurrentAccount.objects.create(
            book=Book.objects.create(name="Demfirat"), code="C-KRV", name="Karven",
            type="supplier", default_currency=usd)
        self.warehouse = a_warehouse()

    def receive(self, *prices):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "current_account_id": self.account.pk, "unit": "mt",
                "products": [{
                    "main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                    "has_variants": True,
                    "variants": [
                        {"name": f"G0{i}", "sku": f"K24644.G0{i}", "price": price,
                         "currency": "USD", "tops": [{"qty": 30}]}
                        for i, price in enumerate(prices, start=1)],
                }],
            }), content_type="application/json")

    def test_it_names_the_line_and_writes_nothing(self):
        response = self.receive("3.50", "-12")

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("K24644.G02", response.json()["error"])
        self.assertNotIn("K24644.G01", response.json()["error"])
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertFalse(Product.objects.filter(sku="K24644").exists())

    def test_a_positive_or_blank_price_still_goes_through(self):
        response = self.receive("3.50", "")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(WarehouseProduct.objects.get(sku="K24644.G01").purchase_price,
                         Decimal("3.50"))
        self.assertIsNone(WarehouseProduct.objects.get(sku="K24644.G02").purchase_price)


class EditingAReceivedPurchaseToANegativePriceIsRefused(received.TestCase):
    setUp = received.ReceivedPurchaseEditTest.setUp
    _invoice = received.ReceivedPurchaseEditTest._invoice
    _edit_url = received.ReceivedPurchaseEditTest._edit_url
    _form = received.ReceivedPurchaseEditTest._form
    _variant = received.ReceivedPurchaseEditTest._variant
    _save = received.ReceivedPurchaseEditTest._save

    def test_the_purchase_is_left_as_it_was(self):
        total_before = self._invoice().total
        form = self._form()
        self._variant(form)["price"] = "-1"

        response = self._save(form)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("negative", response.json()["error"])
        self.assertEqual(self._invoice().total, total_before)
        self.assertFalse(WarehouseProduct.objects.filter(purchase_price__lt=0).exists())


class TheProductEditModalRefusesIt(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username="editor", password="pw", email="e@d.t")
        self.client.force_login(user)
        self.warehouse = a_warehouse()
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="K24644 G07", sku="K24644.G07", quantity=0,
            purchase_price=Decimal("3.50"), purchase_currency="USD", cost_usd=Decimal("3.50"))

    def edit(self, price, name="Renamed"):
        return self.client.post(
            reverse("operating:warehouse_product_edit", args=[self.warehouse.pk, self.wp.pk]),
            {"name": name, "sku": "K24644.G07", "purchase_price": price,
             "purchase_currency": "USD"})

    def test_a_negative_price_changes_nothing_not_even_the_name(self):
        response = self.edit("-3,50")

        self.assertEqual(response.status_code, 400)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.purchase_price, Decimal("3.50"))
        self.assertEqual(self.wp.name, "K24644 G07")


class TheRollScanRefusesItBeforeCreatingAnything(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username="scanner", password="pw", email="s@c.n")
        self.client.force_login(user)
        self.warehouse = a_warehouse()

    def test_no_product_and_no_roll_are_written(self):
        response = self.client.post(
            reverse("operating:warehouse_roll_scan", args=[self.warehouse.pk]),
            {"commit": "true", "sku": "NEW.SKU", "name": "New", "quantity": "30",
             "barcode": "2000043130007", "purchase_price": "-5"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(WarehouseProduct.objects.filter(sku="NEW.SKU").exists())
        self.assertFalse(WarehouseProductItem.objects.exists())


class TheExcelImportSkipsANegativeRowAndSaysSo(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username="importer", password="pw", email="i@m.p")
        self.client.force_login(user)
        self.warehouse = a_warehouse()

    def test_the_other_rows_still_land(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["Name", "Code", "Quantity", "Purchase Price", "Currency"])
        ws.append(["Good", "GOOD1", 10, 4.25, "USD"])
        ws.append(["Bad", "BAD1", 10, -4.25, "USD"])
        upload = io.BytesIO()
        wb.save(upload)
        upload.seek(0)
        upload.name = "stock.xlsx"

        response = self.client.post(
            reverse("operating:warehouse_product_import", args=[self.warehouse.pk]),
            {"file": upload})
        body = b"".join(response.streaming_content).decode()

        self.assertTrue(WarehouseProduct.objects.filter(sku="GOOD1").exists())
        self.assertFalse(WarehouseProduct.objects.filter(sku="BAD1").exists())
        self.assertIn("cannot be negative", body)


class TheReadymadeImportStopsOnTheSheetRow(TestCase):
    def write_sheet(self, path, price):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "GÜNCEL"
        ws.append(["index", "KUTU", "DESEN", "ÖLÇÜ", "RENK", "ASMA TİPİ",
                   "KAP İÇİ SET ADET", "FİYAT/ADET", "FİYAT TOPLAM"])
        ws.append([0, 14, 72010, 84, "KREM", "HALKALI", 5, 19.50, 97.5])
        ws.append([1, 15, 72010, 84, "TURKUAZ", "CEPLİ", 7, price, 0])
        wb.save(path)

    def test_a_negative_price_names_its_row_before_anything_is_written(self):
        import tempfile
        from pathlib import Path
        from django.core.management import CommandError
        from operating.management.commands.import_readymade_stock import read_stock

        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp, "stock.xlsx")
            self.write_sheet(sheet, -18.10)
            with self.assertRaisesMessage(CommandError, "Sheet row 3"):
                read_stock(sheet)

            self.write_sheet(sheet, 18.10)
            self.assertEqual(len(read_stock(sheet)), 2)
