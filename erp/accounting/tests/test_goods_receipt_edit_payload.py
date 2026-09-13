"""The goods-receipt EDIT form and its view have to agree on key names.

A received purchase is reloaded into the form as the form's own payload,
with `invoice_item_id` on every line and `stock_item_id` on every roll it
already has, and the save reads those same two keys back to tell a
correction from an addition. They broke apart once before: commit 8c614c10
renamed the view's side (`roll_id` → `stock_item_id`) while the template
kept the old name, and saving an edited receipt posted nulls and died.

A roll the form posts WITHOUT its id is not an error the view can catch —
it is a new roll, so a mismatch would silently duplicate stock and delete
the original. Hence these checks on both halves.

Run with:
    python manage.py test accounting.test_goods_receipt_edit_payload
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import WarehouseProductItem, Warehouse


class GoodsReceiptEditPayload(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-1", name="Mill", type="supplier",
            default_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Laleli depo", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="edit_admin", password="pw", email="e@d.t"))

        resp = self.client.post(
            reverse("accounts:purchase_order_save",
                    kwargs={"book_id": self.book.pk}),
            data=json.dumps({
                "warehouse_id": self.wh.pk,
                "current_account_id": self.supplier.pk,
                "unit": "mt", "date": "2026-08-21", "notes": "first note",
                "products": [{
                    "main_product": {"mode": "new", "name": "K24644",
                                     "sku": "K24644"},
                    "has_variants": True,
                    "variants": [{"name": "G07", "sku": "K24644.G07",
                                  "price": "3.50", "currency": "USD",
                                  "tops": [{"qty": 30}]}],
                }],
            }), content_type="application/json")
        self.invoice_id = resp.json()["invoice_id"]
        self.client.post(
            reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))

    def _edit_url(self):
        return reverse("operating:warehouse_purchase_edit",
                       args=[self.wh.pk, self.invoice_id])

    def _hydrate(self):
        return self.client.get(
            self._edit_url(),
            headers={"x-requested-with": "XMLHttpRequest"}).json()

    def test_the_hydration_names_the_ids_the_form_reads(self):
        variant = self._hydrate()["products"][0]["variants"][0]
        self.assertIsNotNone(variant.get("invoice_item_id"))
        self.assertIsNotNone(variant["tops"][0].get("stock_item_id"))

    def test_the_hydration_posts_back_as_is(self):
        """npLoadFromPlan → npCollect round-trips the payload untouched, so
        posting what the view served must keep every roll it already had."""
        d = self._hydrate()
        roll_ids = set(WarehouseProductItem.objects.values_list("pk", flat=True))
        resp = self.client.post(
            self._edit_url(),
            data=json.dumps({"warehouse_id": self.wh.pk,
                             "current_account_id": d["current_account_id"],
                             "unit": d["unit"], "notes": "arrived damaged",
                             "products": d["products"]}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            set(WarehouseProductItem.objects.values_list("pk", flat=True)), roll_ids)

    def test_the_template_reads_and_posts_those_same_keys(self):
        with open("accounting/templates/accounts/goods_receipt_form.html",
                  encoding="utf-8") as fh:
            form = fh.read()
        # npFillVariant stores them off the hydration...
        self.assertIn("vEl.dataset.itemId = v.invoice_item_id;", form)
        self.assertIn("row.dataset.stockItemId = t.stock_item_id;", form)
        # ...and npCollect posts them back under the view's names.
        self.assertIn("stock_item_id: npIdOf(row, 'stockItemId')", form)
        self.assertIn("invoice_item_id: npIdOf(v, 'itemId')", form)
        self.assertNotIn("top.roll_id", form)
