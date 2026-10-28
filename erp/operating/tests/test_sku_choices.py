# to run this test, use the command:
# python manage.py test operating.tests.test_sku_choices

"""When a row's values match none of the product's variants, its SKU can
mean a variant renamed or a separate one. The values settle it where they
can — an exact match is that variant, a variant that is the purchase line's
alone is renamed — and the page asks where they can't: a received line's
variant used elsewhere too, or a variant whose values the row only adds to
(white, against white + 320). The save does what was chosen."""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, PurchaseChange
from marketing.models import ProductVariant
from operating.catalog_sync import variant_attributes
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class SkuChoiceTest(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(
            username="sku_choice", password="pw", email="s@c.t"))
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.karven = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier", default_currency=usd)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        # MT-1014.WHITE, received with no width.
        self._receive([{"attributes": [{"name": "color", "value": "white"}],
                        "sku": "MT-1014.WHITE", "tops": [{"qty": 40, "barcode": "W-1"}]}],
                      main={"mode": "new", "name": "MT-1014", "sku": "MT-1014"})
        self.white = ProductVariant.objects.get(variant_sku="MT-1014.WHITE")

    def _receive(self, rows, main=None):
        main = main or {"mode": "existing", "id": self.white.product_id, "sku": "MT-1014"}
        r = self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.wh.pk]),
            data=json.dumps({
                "current_account_id": self.karven.pk, "unit": "m",
                "products": [{"main_product": main, "has_variants": True,
                              "variants": [dict({"price": "2.30", "currency": "USD"}, **row)
                                           for row in rows]}],
            }), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["success"], r.json())
        return r.json()

    def _match(self, attrs, sku):
        return self.client.get(
            reverse("operating:catalog_variant_match", args=[self.wh.pk, self.white.product_id]),
            {"attrs": json.dumps(attrs), "sku": sku}).json()

    def _edit(self, invoice_id):
        url = reverse("operating:warehouse_purchase_edit", args=[self.wh.pk, invoice_id])
        loaded = self.client.get(url, headers={"x-requested-with": "XMLHttpRequest"}).json()
        inv = Invoice.objects.get(pk=invoice_id)
        form = {"warehouse_id": self.wh.pk, "current_account_id": loaded["current_account_id"],
                "unit": loaded["unit"], "date": inv.date.isoformat(), "products": loaded["products"]}
        return url, form

    WHITE_320 = [{"name": "color", "value": "white"}, {"name": "width", "value": "320"}]

    # ── Receiving: values that only add to a variant ────────────────
    def test_the_page_is_asked_about_a_variant_the_values_only_add_to(self):
        d = self._match(self.WHITE_320, "MT-1014.WHITE-320")
        self.assertTrue(d["partial"])
        self.assertEqual(d["variant_sku"], "MT-1014.WHITE")
        self.assertEqual(len(d["uses"]), 1)       # its 40 m from the first delivery

    def test_filling_it_in_renames_it_for_all_its_stock(self):
        r = self._receive([{"attributes": self.WHITE_320, "sku": "MT-1014.WHITE-320",
                            "sku_choice": "rename", "rename_from": "MT-1014.WHITE",
                            "tops": [{"qty": 30, "barcode": "W-2"}]}])
        self.white.refresh_from_db()
        self.assertEqual(self.white.variant_sku, "MT-1014.WHITE-320")
        self.assertEqual(set(variant_attributes(self.white)), {("color", "white"), ("width", "320")})
        # One variant, one row, both deliveries on it.
        wp = WarehouseProduct.objects.get()
        self.assertEqual((wp.sku, wp.catalog_variant, wp.quantity),
                         ("MT-1014.WHITE-320", self.white, Decimal("70.00")))
        self.assertTrue(PurchaseChange.objects.filter(
            invoice_id=r["purchase"]["invoice_id"], field="sku",
            old_value="MT-1014.WHITE", new_value="MT-1014.WHITE-320").exists())

    def test_keeping_it_separate_makes_a_new_variant(self):
        self._receive([{"attributes": self.WHITE_320, "sku": "MT-1014.WHITE-320",
                        "sku_choice": "separate", "tops": [{"qty": 30, "barcode": "W-2"}]}])
        self.white.refresh_from_db()
        self.assertEqual(self.white.variant_sku, "MT-1014.WHITE")
        self.assertEqual(WarehouseProduct.objects.get(sku="MT-1014.WHITE").quantity, Decimal("40.00"))
        self.assertEqual(WarehouseProduct.objects.get(sku="MT-1014.WHITE-320").quantity, Decimal("30.00"))

    def test_an_exact_match_is_that_variant_and_asks_nothing(self):
        d = self._match([{"name": "color", "value": "white"}], "MT-1014.WHITE")
        self.assertTrue(d["exists"])
        self.assertNotIn("partial", d)

    def test_a_direct_receipt_is_logged_and_its_items_linked(self):
        inv = Invoice.objects.get(type="purchase")
        self.assertTrue(PurchaseChange.objects.filter(invoice=inv, action="created").exists())
        self.assertIsNotNone(WarehouseProductItem.objects.get(barcode="W-1").purchase_invoice_item)

    # ── Editing a received line whose variant is used elsewhere ─────
    def _second_delivery(self):
        """A second purchase of MT-1014.WHITE: now neither purchase's line
        has the variant to itself."""
        return self._receive([{"attributes": [{"name": "color", "value": "white"}],
                               "sku": "MT-1014.WHITE", "tops": [{"qty": 30, "barcode": "W-2"}]}])

    def test_a_shared_line_says_what_else_carries_it(self):
        second = self._second_delivery()["purchase"]["invoice_id"]
        _url, form = self._edit(second)
        v = form["products"][0]["variants"][0]
        self.assertFalse(v["sku_follows"])
        self.assertEqual(len(v["sku_uses"]), 1)   # the first delivery's item

    def test_a_shared_line_with_new_values_needs_a_choice(self):
        second = self._second_delivery()["purchase"]["invoice_id"]
        url, form = self._edit(second)
        v = form["products"][0]["variants"][0]
        v["attributes"], v["sku"] = self.WHITE_320, "MT-1014.WHITE-320"
        r = self.client.post(url, data=json.dumps(form), content_type="application/json")
        self.assertEqual(r.status_code, 400, r.content)
        self.white.refresh_from_db()
        self.assertEqual(self.white.variant_sku, "MT-1014.WHITE")

    def test_renaming_a_shared_line_renames_it_for_all(self):
        second = self._second_delivery()["purchase"]["invoice_id"]
        url, form = self._edit(second)
        v = form["products"][0]["variants"][0]
        v.update(attributes=self.WHITE_320, sku="MT-1014.WHITE-320",
                 sku_choice="rename", rename_from="MT-1014.WHITE")
        r = self.client.post(url, data=json.dumps(form), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.white.refresh_from_db()
        self.assertEqual(self.white.variant_sku, "MT-1014.WHITE-320")
        wp = WarehouseProduct.objects.get()
        self.assertEqual((wp.sku, wp.quantity), ("MT-1014.WHITE-320", Decimal("70.00")))
        self.assertTrue(PurchaseChange.objects.filter(
            invoice_id=second, field="sku", new_value="MT-1014.WHITE-320").exists())

    def test_a_separate_variant_takes_only_this_purchases_items(self):
        second = self._second_delivery()["purchase"]["invoice_id"]
        url, form = self._edit(second)
        v = form["products"][0]["variants"][0]
        v.update(attributes=self.WHITE_320, sku="MT-1014.WHITE-320", sku_choice="separate")
        r = self.client.post(url, data=json.dumps(form), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(WarehouseProductItem.objects.get(barcode="W-1").product.sku, "MT-1014.WHITE")
        self.assertEqual(WarehouseProductItem.objects.get(barcode="W-2").product.sku, "MT-1014.WHITE-320")

    def test_stock_gone_out_doesnt_stop_a_confirmed_rename(self):
        roll = WarehouseProductItem.objects.get(barcode="W-1")
        r = self.client.post(
            reverse("operating:warehouse_stock_out", args=[self.wh.pk, roll.product_id]),
            data={"amount": "2", "stock_item_id": roll.pk, "reason": "Samples"})
        self.assertTrue(r.json()["success"], r.json())
        first = Invoice.objects.get(type="purchase").pk
        url, form = self._edit(first)
        v = form["products"][0]["variants"][0]
        self.assertFalse(v["sku_follows"])        # it asks: the 2 m left as MT-1014.WHITE
        v.update(attributes=self.WHITE_320, sku="MT-1014.WHITE-320",
                 sku_choice="rename", rename_from="MT-1014.WHITE")
        r = self.client.post(url, data=json.dumps(form), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(WarehouseProductItem.objects.get(barcode="W-1").product.sku,
                         "MT-1014.WHITE-320")
