"""Our own rolls sent to a supplier to be worked on, on a purchase.

Plain fabric goes to Hakan, crystals or pearls are put on it, and the same
rolls come back as other variants. Hakan is paid per meter. On the purchase
each roll is a processing line: saved, the roll is away (still ours, but not
pickable); received, it becomes its new variant and costs what it did plus
the work, and Hakan is owed meters × price.

Run with:
    scripts/test_local.sh accounting.tests.test_purchase_processing
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, ProcessingLine
from accounting.models_accounts import CurrentAccount, Invoice
from marketing.models import ProductVariant
from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class ProcessingTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene")
        self.mill = CurrentAccount.objects.create(
            book=self.book, code="C-KZL", name="Kizilirmak", type="supplier", default_currency=usd)
        self.hakan = CurrentAccount.objects.create(
            book=self.book, code="C-HKN", name="Hakan", type="supplier", default_currency=usd)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="processing", password="pw", email="p@r.t"))
        self._receive_fabric()
        self.crystal = ProductVariant.objects.get(variant_sku="HAVANA.ECRU_CRYSTAL")
        self.pearl = ProductVariant.objects.get(variant_sku="HAVANA.ECRU_PEARL")

    def _post(self, name, data, how):
        return self.client.post(reverse(name, **how), data=json.dumps(data),
                                content_type="application/json")

    def _receive_fabric(self):
        """Plain ecru on the shelf at $2/m, and one roll each of the crystal
        and pearl variants, so they exist."""
        def variant(value, rolls):
            return {"attributes": [{"name": "color", "value": value}],
                    "sku": "HAVANA." + value.upper().replace("+", "_"),
                    "price": "2", "currency": "USD", "tops": rolls}
        data = {
            "warehouse_id": self.wh.pk, "current_account_id": self.mill.pk,
            "unit": "m", "date": "2026-11-10",
            "products": [{
                "main_product": {"mode": "new", "name": "HAVANA", "sku": "HAVANA"},
                "has_variants": True,
                "variants": [variant("ecru", [{"qty": 50, "barcode": "KZL-A"},
                                              {"qty": 40, "barcode": "KZL-B"}]),
                             variant("ecru+crystal", [{"qty": 10, "barcode": "KZL-C"}]),
                             variant("ecru+pearl", [{"qty": 10, "barcode": "KZL-P"}])],
            }],
        }
        r = self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})
        self.assertTrue(r.json()["success"], r.json())
        confirm = self.client.post(reverse("accounts:purchase_order_confirm",
                                           args=[r.json()["invoice_id"]]))
        self.assertTrue(confirm.json()["success"], confirm.json())

    def _send(self, rows, pk=None):
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.hakan.pk,
                "date": "2026-11-16", "products": [], "processing": rows}
        if pk:
            return self._post("accounts:purchase_order_update", data, {"args": [pk]})
        return self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})

    def _row(self, barcode, variant, price="1.5"):
        return {"barcode": barcode, "to_variant_id": variant.pk, "price": price, "currency": "USD"}

    def _confirm(self, pk):
        return self.client.post(reverse("accounts:purchase_order_confirm", args=[pk]))

    def _roll(self, code):
        return WarehouseProductItem.objects.select_related("product").get(barcode=code)

    def _balance(self, account):
        account.recompute_balance(save=True)
        account.refresh_from_db()
        return account.cached_balance

    # ── sending ──────────────────────────────────────────────────────────
    def test_saved_the_rolls_are_away_and_the_work_is_priced(self, _up):
        r = self._send([self._row("KZL-A", self.crystal), self._row("KZL-B", self.pearl, "2")])
        self.assertTrue(r.json()["success"], r.json())
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        self.assertEqual(inv.status, "ordered")
        # 50 m × 1.5 + 40 m × 2
        self.assertEqual(inv.total, Decimal("155.00"))
        self.assertEqual(inv.items.count(), 2)
        roll = self._roll("KZL-A")
        self.assertTrue(roll.is_away)
        self.assertEqual(roll.product.sku, "HAVANA.ECRU")
        from operating.views import _roll_available_meters
        self.assertEqual(_roll_available_meters(roll), Decimal("0"))
        # Nothing owed before the work comes back.
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    def test_a_roll_taken_off_the_draft_comes_home(self, _up):
        r = self._send([self._row("KZL-A", self.crystal), self._row("KZL-B", self.pearl)])
        pk = r.json()["invoice_id"]
        r = self._send([self._row("KZL-A", self.crystal)], pk=pk)
        self.assertTrue(r.json()["success"], r.json())
        self.assertFalse(self._roll("KZL-B").is_away)
        self.assertTrue(self._roll("KZL-A").is_away)
        self.assertEqual(ProcessingLine.objects.filter(invoice_id=pk).count(), 1)
        self.assertEqual(Invoice.objects.get(pk=pk).total, Decimal("75.00"))

    def test_refusals_change_nothing(self, _up):
        first = self._send([self._row("KZL-A", self.crystal)])
        self.assertTrue(first.json()["success"])
        cases = [
            ([self._row("KZL-A", self.pearl)], "already away"),
            ([self._row("KZL-C", self.crystal)], "already"),
            ([self._row("NOPE", self.crystal)], "not found"),
            ([self._row("KZL-B", self.crystal), self._row("KZL-B", self.pearl)], "twice"),
            ([{"barcode": "KZL-B", "price": "1"}], "become"),
        ]
        for rows, words in cases:
            r = self._send(rows)
            self.assertEqual(r.status_code, 400, (rows, r.content))
            self.assertIn(words, r.json()["error"])
        self.assertEqual(Invoice.objects.filter(current_account=self.hakan).count(), 1)
        self.assertFalse(self._roll("KZL-B").is_away)

    def test_a_roll_reserved_for_an_order_is_refused(self, _up):
        roll = self._roll("KZL-B")
        order = Order.objects.create()
        OrderStockReservation.objects.create(order=order, stock_item=roll,
                                             warehouse_product=roll.product,
                                             quantity=Decimal("40"))
        r = self._send([self._row("KZL-B", self.crystal)])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("reserved", r.json()["error"])

    def test_a_roll_of_another_book_is_refused(self, _up):
        other = Book.objects.create(name="Laleli")
        far = Warehouse.objects.create(name="Laleli store", accounting_book=other)
        WarehouseProduct.objects.filter(warehouse=self.wh, sku="HAVANA.ECRU").update(warehouse=far)
        r = self._send([self._row("KZL-A", self.crystal)])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Laleli", r.json()["error"])

    # ── receiving ────────────────────────────────────────────────────────
    def test_received_each_roll_becomes_its_variant_and_costs_the_work_more(self, _up):
        r = self._send([self._row("KZL-A", self.crystal), self._row("KZL-B", self.pearl, "2")])
        pk = r.json()["invoice_id"]
        c = self._confirm(pk)
        self.assertTrue(c.json()["success"], c.json())

        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, b.product.sku), ("HAVANA.ECRU_CRYSTAL", "HAVANA.ECRU_PEARL"))
        self.assertEqual((a.unit_cost_base, b.unit_cost_base), (Decimal("3.5"), Decimal("4")))
        self.assertFalse(a.is_away or b.is_away)
        self.assertEqual(WarehouseProduct.objects.get(warehouse=self.wh, sku="HAVANA.ECRU").quantity,
                         Decimal("0"))
        self.assertEqual(WarehouseProduct.objects.get(warehouse=self.wh,
                                                      sku="HAVANA.ECRU_CRYSTAL").quantity,
                         Decimal("60"))
        inv = Invoice.objects.get(pk=pk)
        self.assertEqual((inv.status, inv.total), ("received", Decimal("155.00")))
        self.assertEqual(self._balance(self.hakan), Decimal("-155.00"))
        self.assertTrue(all(l.invoice_item_id for l in inv.processing_lines.all()))

    def test_the_ledger_carries_what_the_shelves_now_hold(self, _up):
        from accounting.services_ledger import reconcile
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        self.assertTrue(self._confirm(pk).json()["success"])
        row = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1300")
        # $2 × 110 m of fabric and $1.5 × 50 m of work.
        self.assertEqual(row["subsidiary"], Decimal("295"))
        self.assertEqual(row["ledger"], row["subsidiary"])

    # ── undo and cancel ──────────────────────────────────────────────────
    def test_undo_receipt_puts_each_roll_back_and_away_again(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        self.assertTrue(self._confirm(pk).json()["success"])
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 200, r.content)
        roll = self._roll("KZL-A")
        self.assertEqual((roll.product.sku, roll.unit_cost_base), ("HAVANA.ECRU", Decimal("2")))
        self.assertTrue(roll.is_away)
        inv = Invoice.objects.get(pk=pk)
        self.assertEqual((inv.status, inv.total), ("ordered", Decimal("75.00")))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))
        self.assertTrue(self._confirm(pk).json()["success"])
        self.assertEqual(self._roll("KZL-A").product.sku, "HAVANA.ECRU_CRYSTAL")

    def test_undo_is_refused_once_the_roll_is_cut(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        self.assertTrue(self._confirm(pk).json()["success"])
        WarehouseProductItem.objects.filter(barcode="KZL-A").update(quantity_remaining=Decimal("45"))
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 422, r.content)
        self.assertEqual(Invoice.objects.get(pk=pk).status, "received")

    def test_cancelling_a_draft_brings_the_rolls_home(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "not sent"})
        self.assertEqual(r.status_code, 200, r.content)
        roll = self._roll("KZL-A")
        self.assertFalse(roll.is_away)
        self.assertEqual(roll.product.sku, "HAVANA.ECRU")

    def test_cancelling_a_received_one_puts_the_rolls_back(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        self.assertTrue(self._confirm(pk).json()["success"])
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "wrong"})
        self.assertEqual(r.status_code, 200, r.content)
        roll = self._roll("KZL-A")
        self.assertEqual((roll.product.sku, roll.unit_cost_base, roll.is_away),
                         ("HAVANA.ECRU", Decimal("2"), False))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    def test_the_rolls_original_purchase_page_still_opens(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        self.assertTrue(self._confirm(pk).json()["success"])
        original = self._roll("KZL-B").purchase_invoice_item.invoice
        for name in ("accounts:purchase_order_detail",):
            self.assertEqual(self.client.get(reverse(name, args=[original.pk])).status_code, 200)
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 200)

    # ── the form and the page ────────────────────────────────────────────
    def test_the_form_looks_a_roll_up_with_what_it_can_become(self, _up):
        url = reverse("accounts:processing_roll", args=[self.hakan.pk])
        d = self.client.get(url, {"code": "KZL-A"}).json()
        self.assertTrue(d["ok"], d)
        self.assertEqual((d["roll"]["sku"], d["roll"]["quantity"], d["roll"]["problem"]),
                         ("HAVANA.ECRU", "50", None))
        self.assertEqual({v["sku"] for v in d["roll"]["variants"]},
                         {"HAVANA.ECRU_CRYSTAL", "HAVANA.ECRU_PEARL"})
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        away = self.client.get(url, {"code": "KZL-A"}).json()["roll"]["problem"]
        self.assertIn("already away", away)
        # The purchase it is away on may show it, though.
        self.assertIsNone(self.client.get(url, {"code": "KZL-A", "purchase": pk})
                          .json()["roll"]["problem"])
        self.assertEqual(self.client.get(url, {"code": "NOPE"}).status_code, 404)

    def test_the_purchase_page_lists_the_rolls_before_and_after(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        page = reverse("accounts:purchase_order_detail", args=[pk])
        r = self.client.get(page)
        self.assertContains(r, "Our rolls away being worked on")
        self.assertContains(r, "KZL-A")
        self.assertTrue(self._confirm(pk).json()["success"])
        r = self.client.get(page)
        self.assertContains(r, "Our rolls worked on")
        self.assertNotContains(r, reverse("accounts:goods_receipt_edit", args=[pk]))

    def test_a_draft_opens_in_the_form(self, _up):
        pk = self._send([self._row("KZL-A", self.crystal)]).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="npWorkSec"')
        self.assertContains(r, '"processing"')
