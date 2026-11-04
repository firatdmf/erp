"""A purchase received by mistake, or too soon, can be taken back to an order.

PO 171 was meant to be saved as a draft and was received instead; the only
way back was Cancel, which would also have cancelled the customer's order.
Undo receipt takes the stock back off the shelf and the supplier debt out of
the ledger, and leaves an order with the same rolls planned — barcodes
included — to be received when the goods arrive. It refuses while any of
the stock has been used.

Run with:
    python manage.py test accounting.tests.test_undo_purchase_receipt
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from operating.models import (OrderStockReservation, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class UndoReceiptTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="C-KZL", name="Kizilirmak", type="supplier", default_currency=usd)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="undo_receipt", password="pw", email="u@r.t"))

    def _receive(self, _up, customer=None):
        from crm.models import Contact
        data = {
            "warehouse_id": self.wh.pk, "current_account_id": self.supplier.pk,
            "unit": "m", "date": "2026-11-03",
            "products": [{
                "main_product": {"mode": "new", "name": "HAVANA", "sku": "HAVANA"},
                "has_variants": True,
                "variants": [{"attributes": [{"name": "color", "value": "ecru"}],
                              "sku": "HAVANA.ECRU", "price": "1", "currency": "USD",
                              "sale_price": "1.70",
                              "tops": [{"qty": 50, "barcode": "KZL-A"},
                                       {"qty": 50, "barcode": "KZL-B"}]}],
            }],
        }
        if customer:
            data["customer"] = {"type": "contact", "pk": Contact.objects.create(name="Oleg").pk}
        r = self.client.post(reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
                             data=json.dumps(data), content_type="application/json")
        self.invoice_id = r.json()["invoice_id"]
        confirm = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))
        self.assertTrue(confirm.json()["success"], confirm.json())
        return Invoice.objects.get(pk=self.invoice_id)

    def _undo(self):
        return self.client.post(reverse("accounts:purchase_undo_receipt", args=[self.invoice_id]))

    def _balance(self):
        self.supplier.recompute_balance(save=True)
        self.supplier.refresh_from_db()
        return self.supplier.cached_balance

    def test_the_receipt_is_taken_back_to_an_order(self, _up):
        inv = self._receive(_up)
        self.assertEqual(self._balance(), Decimal("-100.00"))

        r = self._undo()
        self.assertEqual(r.status_code, 200, r.content)
        inv.refresh_from_db()
        self.assertEqual((inv.status, inv.received_on, inv.posted_movement_id),
                         ("ordered", None, None))
        self.assertEqual(self._balance(), Decimal("0.00"))
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertEqual(WarehouseProduct.objects.get(sku="HAVANA.ECRU").quantity, Decimal("0"))
        self.assertEqual(inv.total, Decimal("100.00"))
        self.assertEqual(list(inv.items.values_list("quantity", flat=True)), [Decimal("100.000")])
        tops = inv.intake_plan["products"][0]["variants"][0]["tops"]
        self.assertEqual([t["barcode"] for t in tops], ["KZL-A", "KZL-B"])
        self.assertEqual(inv.change_logs.filter(action="status").order_by("pk")
                         .values_list("old_value", "new_value").last(), ("received", "ordered"))

    def test_the_page_offers_it_while_received(self, _up):
        self._receive(_up)
        page = reverse("accounts:purchase_order_detail", args=[self.invoice_id])
        self.assertContains(self.client.get(page), 'id="poUndoBtn"')
        self.assertEqual(self._undo().status_code, 200)
        self.assertNotContains(self.client.get(page), 'id="poUndoBtn"')

    def test_it_can_be_received_again_with_the_same_labels(self, _up):
        self._receive(_up)
        self.assertEqual(self._undo().status_code, 200)
        again = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))
        self.assertTrue(again.json()["success"], again.json())
        inv = Invoice.objects.get(pk=self.invoice_id)
        self.assertEqual(inv.status, "received")
        self.assertEqual(inv.total, Decimal("100.00"))
        self.assertEqual(sorted(WarehouseProductItem.objects.values_list("barcode", flat=True)),
                         ["KZL-A", "KZL-B"])
        self.assertEqual(self._balance(), Decimal("-100.00"))

    def test_a_roll_cut_since_refuses_it_and_changes_nothing(self, _up):
        inv = self._receive(_up)
        WarehouseProductItem.objects.filter(barcode="KZL-A").update(quantity_remaining=Decimal("45"))
        r = self._undo()
        self.assertEqual(r.status_code, 422, r.content)
        self.assertTrue(any("KZL-A" in b for b in r.json()["blocked"]))
        inv.refresh_from_db()
        self.assertEqual(inv.status, "received")
        self.assertEqual(WarehouseProductItem.objects.count(), 2)
        self.assertEqual(self._balance(), Decimal("-100.00"))

    def test_an_ordered_purchase_has_no_receipt_to_undo(self, _up):
        self._receive(_up)
        self.assertEqual(self._undo().status_code, 200)
        self.assertEqual(self._undo().status_code, 400)

    def test_bought_for_a_customer_the_order_stays_and_waits_again(self, _up):
        inv = self._receive(_up, customer=True)
        order = inv.for_order
        self.assertEqual(OrderStockReservation.objects.filter(order=order).count(), 2)

        r = self._undo()
        self.assertEqual(r.status_code, 200, r.content)
        order.refresh_from_db()
        self.assertNotEqual(order.order_status, "cancelled")
        self.assertEqual(list(order.items.values_list("product_variant__variant_sku", "quantity")),
                         [("HAVANA.ECRU", Decimal("100.00"))])
        self.assertFalse(OrderStockReservation.objects.filter(order=order).exists())
        self.assertEqual(list(order.unreceived_purchases()), [Invoice.objects.get(pk=self.invoice_id)])
        self.assertEqual(Invoice.objects.get(pk=self.invoice_id).intake_plan["customer"]["type"],
                         "contact")
