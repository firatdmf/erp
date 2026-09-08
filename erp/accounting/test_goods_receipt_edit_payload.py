"""The goods-receipt EDIT form and its view have to agree on key names.

test_purchase_order_flow's `_current_diff` hand-writes the edit payload
using the VIEW's key names, so it stayed green while the template sent
something else entirely. Commit 8c614c10 ("Let stock remember what it
cost, and call it stock") renamed the view's side — `roll_id` became
`stock_item_id` on the way out, `new_tops` became `new_stock` on the way
in — and the template kept both old names. Saving an edited receipt then
posted `kept_roll_ids: [null]` (parseInt("undefined") → NaN → JSON null)
and died on `int(None)`, while any newly added stock sat in a `new_tops`
key nothing read.

These tests build the payload the way npCollectEditPayload does, off the
keys the view really serves, so the two halves can't drift apart again.

Run with:
    python manage.py test accounting.test_goods_receipt_edit_payload
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, Invoice
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

    def _template_payload(self, hydrated, new_stock=()):
        """Exactly what npCollectEditPayload builds: the id it reads off
        each existing chip is whatever npAddExistingTop put in the
        dataset, so this reads the SAME key the template does."""
        return [{
            "main_product": {"mode": "existing"},
            "variants": [{
                "invoice_item_id": v["invoice_item_id"],
                "warehouse_product_id": v["warehouse_product_id"],
                "kept_roll_ids": [t["stock_item_id"] for t in v["tops"]],
                "new_stock": list(new_stock),
            } for v in group["variants"]],
        } for group in hydrated["products"]]

    def test_the_hydration_names_the_id_the_form_reads(self):
        """npAddExistingTop stores top.stock_item_id — if the view ever
        stops serving that key, every chip's dataset id goes undefined
        and the save posts nulls."""
        top = self._hydrate()["products"][0]["variants"][0]["tops"][0]
        self.assertIn("stock_item_id", top)
        self.assertIsNotNone(top["stock_item_id"])

    def test_the_form_can_save_an_untouched_receipt(self):
        payload = self._template_payload(self._hydrate())
        resp = self.client.post(
            self._edit_url(),
            data=json.dumps({"unit": "mt", "notes": "arrived damaged",
                             "products": payload}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            Invoice.objects.get(pk=self.invoice_id).notes, "arrived damaged")
        # Every stock item was named as kept, so none was removed.
        self.assertEqual(WarehouseProductItem.objects.count(), 1)

    def test_stock_added_during_an_edit_actually_lands(self):
        """The container key has to be the one the view reads, or the
        new stock is dropped without a word."""
        payload = self._template_payload(
            self._hydrate(), new_stock=[{"qty": 12, "barcode": ""}])
        resp = self.client.post(
            self._edit_url(),
            data=json.dumps({"unit": "mt", "notes": "plus one roll",
                             "products": payload}),
            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(WarehouseProductItem.objects.count(), 2)
        self.assertEqual(
            sorted(r.quantity for r in WarehouseProductItem.objects.all()),
            [Decimal("12.00"), Decimal("30.00")])

    def test_the_template_posts_those_same_two_keys(self):
        """Guards the client half — the view is only ever reached with
        the names npCollectEditPayload writes."""
        with open("accounting/templates/accounts/goods_receipt_form.html",
                  encoding="utf-8") as fh:
            form = fh.read()
        self.assertIn("row.dataset.rollId = top.stock_item_id;", form)
        self.assertIn("new_stock: newTops,", form)
        self.assertNotIn("top.roll_id", form)
        self.assertNotIn("new_tops:", form)
