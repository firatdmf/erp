# to run this test, use the command:
# python manage.py test accounting.test_purchase_edit_gone_out_rolls

"""What the purchase form may still change about a roll depends on what has
happened to it since it arrived.

Once metres have gone out of a roll — shipped on an order, or taken off by
hand — its length, barcode and variant are that record, and it can't come
off the purchase. The price is still what was paid, so that stays open. A
roll only reserved can still be re-measured; the page is told who holds it,
oldest first, so it can name the orders a shorter length would cut before
the save."""
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from accounting import test_received_purchase_edit as base
from operating.models import (Order, OrderItem, OrderStockReservation,
                              WarehouseProduct, WarehouseProductItem)


class PurchaseEditGoneOutRollsTest(base.TestCase):
    setUp = base.ReceivedPurchaseEditTest.setUp
    _invoice = base.ReceivedPurchaseEditTest._invoice
    _roll = base.ReceivedPurchaseEditTest._roll
    _edit_url = base.ReceivedPurchaseEditTest._edit_url
    _form = base.ReceivedPurchaseEditTest._form
    _variant = base.ReceivedPurchaseEditTest._variant
    _save = base.ReceivedPurchaseEditTest._save
    _reserve = base.ReceivedPurchaseEditTest._reserve

    def _stock_out(self, barcode, metres):
        roll = self._roll(barcode)
        r = self.client.post(
            reverse("operating:warehouse_stock_out", args=[self.wh.pk, roll.product_id]),
            data={"amount": str(metres), "stock_item_id": roll.pk, "reason": "Samples"})
        self.assertTrue(r.json()["success"], r.json())

    def _assert_refused(self, form, barcode):
        before = sorted(WarehouseProductItem.objects.values_list(
            "pk", "barcode", "quantity", "quantity_remaining", "product_id"))
        form["notes"] = "must not stick"
        r = self._save(form)
        self.assertEqual(r.status_code, 422, r.content)
        self.assertEqual([b["barcode"] for b in r.json()["blocked"]], [barcode])
        self.assertEqual(sorted(WarehouseProductItem.objects.values_list(
            "pk", "barcode", "quantity", "quantity_remaining", "product_id")), before)
        self.assertEqual(self._invoice().notes, "first note")

    # ── Loading ─────────────────────────────────────────────────────
    def test_the_page_is_told_what_went_out_and_who_holds_what(self):
        self._stock_out("KRV-A", 2)
        first = self._reserve("KRV-B", "8")
        with patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png"):
            order = Order.objects.create(order_number="DK-KRV-B-2", order_status="pending")
            item = OrderItem.objects.create(order=order, product=first.order_item.product,
                                            quantity=10, price=10)
            second = OrderStockReservation.objects.create(
                order=order, order_item=item, stock_item=first.stock_item,
                warehouse_product=first.warehouse_product, quantity=Decimal("10"))

        tops = self._variant(self._form())["tops"]
        self.assertEqual([t["out"] for t in tops], [2.0, 0.0])
        self.assertEqual(tops[0]["holds"], [])
        self.assertEqual(tops[1]["holds"], [
            {"label": str(first.order), "qty": 8.0},
            {"label": str(second.order), "qty": 10.0},
        ])

    # ── A roll metres have gone out of ──────────────────────────────
    def test_saving_it_untouched_is_fine(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        form["notes"] = "checked"
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._invoice().notes, "checked")

    def test_its_length_cant_change_even_longer(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        self._variant(form)["tops"][0]["qty"] = "32"
        self._assert_refused(form, "KRV-A")

    def test_its_barcode_cant_change(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        self._variant(form)["tops"][0]["barcode"] = "KRV-A2"
        self._assert_refused(form, "KRV-A")

    def test_it_cant_be_removed_even_with_no_order_behind_it(self):
        self._stock_out("KRV-B", 5)
        form = self._form()
        self._variant(form)["tops"].pop(1)
        self._assert_refused(form, "KRV-B")

    def test_it_cant_become_another_variant(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        v = self._variant(form)
        v["name"], v["sku"] = "G08", "K24644.G08"
        self._assert_refused(form, "KRV-A")
        self.assertFalse(WarehouseProduct.objects.filter(sku="K24644.G08").exists())

    def test_its_price_can_still_be_corrected(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        self._variant(form)["price"] = "4"
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._invoice().total, Decimal("200.00"))
        self.assertEqual(self._roll("KRV-A").unit_cost_base, Decimal("4"))

    def test_the_other_rolls_on_its_line_stay_editable(self):
        self._stock_out("KRV-A", 2)
        form = self._form()
        self._variant(form)["tops"][1]["qty"] = "19"
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._roll("KRV-B").quantity, Decimal("19.00"))
        self.assertEqual(self._invoice().items.get().quantity, Decimal("49.000"))

    # ── The page ────────────────────────────────────────────────────
    def test_the_form_renders_with_the_warnings(self):
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[self.invoice_id]))
        self.assertContains(r, "Saving will reduce what these orders have reserved:")
        self.assertContains(r, "its length and barcode can\\u0027t change")
