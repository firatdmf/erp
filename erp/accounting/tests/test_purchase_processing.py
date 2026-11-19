"""Our own rolls sent out to a supplier to be worked on: goods out and in.

Plain fabric goes to Hakan, crystals or pearls go on it, and the work comes
back. On the purchase the plain rolls are goods out; what comes back is its
ordinary products (goods in), priced at the work. A goods-in roll with an
out roll's barcode is that roll come back; out rolls that don't come back
were used up in the work. The value of everything that went out is spread
per unit over everything that came in, and Hakan is owed only the work.

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
from crm.models import Company
from marketing.models import Product
from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class GoodsOutTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene")
        self.mill = CurrentAccount.objects.create(
            book=self.book, code="C-KZL", name="Kizilirmak", type="supplier", default_currency=usd)
        self.hakan_co = Company.objects.create(name="Hakan Atölye")
        self.hakan = CurrentAccount.objects.create(
            book=self.book, code="C-HKN", name="Hakan Atölye", type="supplier",
            default_currency=usd, company=self.hakan_co)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="processing", password="pw", email="p@r.t"))
        self._receive_fabric()
        self.product = Product.objects.get(sku="HAVANA")

    # ── helpers ──────────────────────────────────────────────────────────
    def _post(self, name, data, how):
        return self.client.post(reverse(name, **how), data=json.dumps(data),
                                content_type="application/json")

    @staticmethod
    def _variant(value, tops, price="2"):
        return {"attributes": [{"name": "color", "value": value}],
                "sku": "HAVANA." + value.upper().replace("+", "_"),
                "price": price, "currency": "USD", "tops": tops}

    def _receive_fabric(self):
        """Plain ecru at $2/m, and a roll each of crystal and pearl."""
        data = {
            "warehouse_id": self.wh.pk, "current_account_id": self.mill.pk,
            "unit": "m", "date": "2026-11-10",
            "products": [{
                "main_product": {"mode": "new", "name": "HAVANA", "sku": "HAVANA"},
                "has_variants": True,
                "variants": [self._variant("ecru", [{"qty": 50, "barcode": "KZL-A"},
                                                    {"qty": 40, "barcode": "KZL-B"}]),
                             self._variant("ecru+crystal", [{"qty": 10, "barcode": "KZL-C"}]),
                             self._variant("ecru+pearl", [{"qty": 10, "barcode": "KZL-P"}])],
            }],
        }
        r = self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})
        self.assertTrue(r.json()["success"], r.json())
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[r.json()["invoice_id"]]))
        self.assertTrue(c.json()["success"], c.json())

    def _goods_in(self, *variants):
        return [{"main_product": {"mode": "existing", "id": self.product.pk,
                                  "title": "HAVANA", "sku": "HAVANA"},
                 "has_variants": True, "variants": list(variants)}]

    def _save(self, out, goods_in=(), pk=None):
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.hakan.pk,
                "date": "2026-11-16", "unit": "m",
                "goods_out": [{"barcode": c} for c in out], "products": list(goods_in)}
        if pk:
            return self._post("accounts:purchase_order_update", data, {"args": [pk]})
        return self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})

    def _confirm(self, pk):
        return self.client.post(reverse("accounts:purchase_order_confirm", args=[pk]))

    def _roll(self, code):
        return WarehouseProductItem.objects.select_related("product").get(barcode=code)

    def _balance(self, account):
        account.recompute_balance(save=True)
        account.refresh_from_db()
        return account.cached_balance

    def _sent_and_back(self):
        """A and B go out; A comes back as 48 m of crystal at $1.50, and a
        new 38 m roll of pearl at $2; B was used up."""
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        r = self._save(["KZL-A", "KZL-B"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5"),
            self._variant("ecru+pearl", [{"qty": 38, "barcode": ""}], price="2")), pk=pk)
        self.assertTrue(r.json()["success"], r.json())
        c = self._confirm(pk)
        self.assertTrue(c.json()["success"], c.json())
        return pk

    # ── sending ──────────────────────────────────────────────────────────
    def test_goods_out_alone_is_an_order_and_the_rolls_are_away(self, _up):
        r = self._save(["KZL-A", "KZL-B"])
        self.assertTrue(r.json()["success"], r.json())
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        self.assertEqual((inv.status, inv.total), ("ordered", Decimal("0.00")))
        self.assertEqual(ProcessingLine.objects.filter(invoice=inv).count(), 2)
        roll = self._roll("KZL-A")
        self.assertTrue(roll.is_away)
        from operating.views import _roll_available_meters
        self.assertEqual(_roll_available_meters(roll), Decimal("0"))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    def test_a_roll_taken_off_goods_out_comes_home(self, _up):
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        self.assertTrue(self._save(["KZL-A"], pk=pk).json()["success"])
        self.assertFalse(self._roll("KZL-B").is_away)
        self.assertTrue(self._roll("KZL-A").is_away)

    def test_refusals_change_nothing(self, _up):
        self.assertTrue(self._save(["KZL-A"]).json()["success"])
        for out, words in ((["KZL-A"], "already away"), (["NOPE"], "Nothing in stock"),
                           (["KZL-B", "KZL-B"], "twice")):
            r = self._save(out)
            self.assertEqual(r.status_code, 400, (out, r.content))
            self.assertIn(words, r.json()["error"])
        self.assertEqual(Invoice.objects.filter(current_account=self.hakan).count(), 1)
        self.assertFalse(self._roll("KZL-B").is_away)

    def test_a_roll_reserved_for_an_order_is_refused(self, _up):
        roll = self._roll("KZL-B")
        OrderStockReservation.objects.create(order=Order.objects.create(), stock_item=roll,
                                             warehouse_product=roll.product, quantity=Decimal("40"))
        r = self._save(["KZL-B"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("reserved", r.json()["error"])

    def test_a_roll_of_another_book_is_refused(self, _up):
        far = Warehouse.objects.create(name="Laleli store",
                                       accounting_book=Book.objects.create(name="Laleli"))
        WarehouseProduct.objects.filter(warehouse=self.wh, sku="HAVANA.ECRU").update(warehouse=far)
        r = self._save(["KZL-A"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Laleli", r.json()["error"])

    # ── receiving ────────────────────────────────────────────────────────
    def test_receiving_needs_goods_in(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self._confirm(pk)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("came back", r.json()["error"])
        self.assertTrue(self._roll("KZL-A").is_away)

    def test_a_returned_roll_keeps_its_record_and_the_rest_were_used_up(self, _up):
        pk = self._sent_and_back()
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity, a.quantity_remaining, a.is_away),
                         ("HAVANA.ECRU_CRYSTAL", Decimal("48"), Decimal("48"), False))
        self.assertEqual((b.status, b.quantity_remaining, b.is_away), ("consumed", 0, False))
        self.assertEqual(WarehouseProductItem.objects.filter(barcode="KZL-A").count(), 1)
        lines = {l.barcode: l.outcome for l in ProcessingLine.objects.filter(invoice_id=pk)}
        self.assertEqual(lines, {"KZL-A": "returned", "KZL-B": "used"})

    def test_what_went_out_is_spread_over_what_came_in_and_only_the_work_is_owed(self, _up):
        pk = self._sent_and_back()
        # 90 m at $2 went out = $180, over 86 m that came in.
        share = Decimal("180") / Decimal("86")
        a = self._roll("KZL-A")
        pearl = (WarehouseProductItem.objects
                 .filter(product__sku="HAVANA.ECRU_PEARL", quantity=Decimal("38")).get())
        self.assertAlmostEqual(a.unit_cost_base, Decimal("1.5") + share, places=3)
        self.assertAlmostEqual(pearl.unit_cost_base, Decimal("2") + share, places=3)
        # 48 × 1.50 + 38 × 2
        self.assertEqual(Invoice.objects.get(pk=pk).total, Decimal("148.00"))
        self.assertEqual(self._balance(self.hakan), Decimal("-148.00"))

    def test_only_its_own_goods_out_may_come_back_under_their_barcode(self, _up):
        """KZL-A went out, so it may come back as KZL-A. KZL-C is in stock
        and did not go out: its barcode is someone else's, and is refused."""
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        self._save(["KZL-A"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-C"}], price="1.5")), pk=pk)
        r = self._confirm(pk)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("KZL-C", r.json()["error"])
        self.assertEqual(Invoice.objects.get(pk=pk).status, "ordered")
        self.assertTrue(self._roll("KZL-A").is_away)
        self.assertEqual(WarehouseProductItem.objects.filter(barcode="KZL-C").count(), 1)

    def test_the_ledger_still_matches_the_shelves(self, _up):
        from accounting.services_ledger import reconcile
        self._sent_and_back()
        row = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1300")
        # $220 of fabric before, plus $148 of work.
        self.assertAlmostEqual(row["ledger"], Decimal("368"), places=2)
        self.assertAlmostEqual(row["subsidiary"], row["ledger"], places=2)

    # ── undo and cancel ──────────────────────────────────────────────────
    def test_undo_receipt_puts_every_out_roll_back_and_away_again(self, _up):
        pk = self._sent_and_back()
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 200, r.content)
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity_remaining, a.unit_cost_base, a.is_away),
                         ("HAVANA.ECRU", Decimal("50"), Decimal("2"), True))
        self.assertEqual((b.status, b.quantity_remaining, b.is_away), ("in_stock", Decimal("40"), True))
        self.assertFalse(WarehouseProductItem.objects.filter(
            product__sku="HAVANA.ECRU_PEARL", quantity=Decimal("38")).exists())
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))
        self.assertTrue(self._confirm(pk).json()["success"])
        self.assertEqual(self._roll("KZL-A").product.sku, "HAVANA.ECRU_CRYSTAL")

    def test_undo_is_refused_once_a_returned_roll_is_cut(self, _up):
        pk = self._sent_and_back()
        WarehouseProductItem.objects.filter(barcode="KZL-A").update(quantity_remaining=Decimal("45"))
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 422, r.content)
        self.assertEqual(Invoice.objects.get(pk=pk).status, "received")

    def test_cancelling_a_draft_brings_the_rolls_home(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "not sent"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(self._roll("KZL-A").is_away)

    def test_cancelling_a_received_one_puts_the_rolls_back(self, _up):
        pk = self._sent_and_back()
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "wrong"})
        self.assertEqual(r.status_code, 200, r.content)
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity_remaining, a.is_away),
                         ("HAVANA.ECRU", Decimal("50"), False))
        self.assertEqual((b.status, b.is_away), ("in_stock", False))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    # ── where it shows ───────────────────────────────────────────────────
    def test_the_form_looks_a_roll_up(self, _up):
        url = reverse("accounts:processing_roll", args=[self.hakan.pk])
        d = self.client.get(url, {"code": "KZL-A"}).json()
        self.assertEqual((d["roll"]["sku"], d["roll"]["quantity"], d["roll"]["problem"]),
                         ("HAVANA.ECRU", "50", None))
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        self.assertIn("already away", self.client.get(url, {"code": "KZL-A"}).json()["roll"]["problem"])
        self.assertIsNone(self.client.get(url, {"code": "KZL-A", "purchase": pk})
                          .json()["roll"]["problem"])
        self.assertEqual(self.client.get(url, {"code": "NOPE"}).status_code, 404)

    def test_the_purchase_page_shows_goods_out_and_what_became_of_them(self, _up):
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        page = reverse("accounts:purchase_order_detail", args=[pk])
        r = self.client.get(page)
        self.assertContains(r, "Our goods sent out")
        self.assertContains(r, "away")
        self._save(["KZL-A", "KZL-B"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5")), pk=pk)
        self.assertTrue(self._confirm(pk).json()["success"])
        r = self.client.get(page)
        self.assertContains(r, "came back")
        self.assertContains(r, "used up in the work")
        self.assertNotContains(r, reverse("accounts:goods_receipt_edit", args=[pk]))

    def test_a_returned_roll_shows_and_prints_under_the_line_it_came_back_as(self, _up):
        pk = self._sent_and_back()
        inv = Invoice.objects.get(pk=pk)
        crystal = inv.items.get(variant__variant_sku="HAVANA.ECRU_CRYSTAL")
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[pk]))
        self.assertContains(page, "<code>KZL-A</code>", html=False)
        with patch("operating.warehouse_label.labels_pdf_bytes", return_value=b"%PDF") as pdf:
            r = self.client.get(reverse("accounts:purchase_item_labels", args=[pk, crystal.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([roll.barcode for _wp, roll in pdf.call_args[0][0]], ["KZL-A"])

    def test_rolls_away_show_on_the_list_and_on_the_suppliers_page(self, _up):
        self._save(["KZL-A", "KZL-B"])
        lst = self.client.get(reverse("accounts:purchase_order_list", kwargs={"book_id": self.book.pk}))
        self.assertContains(lst, "2 items away · 90 m")
        crm = self.client.get(reverse("crm:company_detail", args=[self.hakan_co.pk]))
        self.assertContains(crm, "2 items away · 90 m")

    def test_a_draft_opens_in_the_form_with_its_goods_out(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="npWorkSec"')
        # Several barcodes at once, one a line.
        self.assertContains(r, '<textarea id="npWorkCode"')
        self.assertContains(r, '"goods_out"')
