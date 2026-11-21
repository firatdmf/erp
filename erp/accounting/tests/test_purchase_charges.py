"""A purchase's delivery cost: owed to the carrier, part of the goods' cost.

The purchase: 30 m (KRV-A) and 20 m (KRV-B) of one variant at 3.50 from
Karven, 175.00 owed to Karven. The carrier, Öz Turanlar, brought it and
charges its own account for that. Received, the charge is a payable on
the carrier's card and is spread over the rolls per unit; meters that
left before the charge arrived take their share into cost of goods sold.

Run with:
    scripts/test_local.sh accounting.tests.test_purchase_charges
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, PurchaseCharge
from accounting.models_accounts import CurrentAccount, Invoice
from accounting.services_ledger import balance_sheet, reconcile
from operating.models import Warehouse, WarehouseProductItem


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class PurchaseChargeTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.karven = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier", default_currency=self.usd)
        self.carrier = CurrentAccount.objects.create(
            book=self.book, code="C-DGN", name="Öz Turanlar", type="supplier",
            default_currency=self.usd)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="charges", password="pw", email="c@h.t"))

    # ── helpers ─────────────────────────────────────────────────────
    def _payload(self, charges=None, lengths=(30, 20), extra_variant=None):
        variants = [{"name": "G07", "sku": "K24644.G07", "price": "3.50", "currency": "USD",
                     "tops": [{"qty": q, "barcode": f"KRV-{chr(65 + i)}"}
                              for i, q in enumerate(lengths)]}]
        if extra_variant:
            variants.append(extra_variant)
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.karven.pk,
                "unit": "m", "date": "2026-11-20",
                "products": [{"main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                              "has_variants": True, "variants": variants}]}
        if charges is not None:
            data["charges"] = charges
        return data

    def _charge(self, amount, account=None, **kw):
        return {"account_id": (account or self.carrier).pk, "description": "Delivery",
                "amount": str(amount), **kw}

    def _save_order(self, data):
        r = self.client.post(reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
                             data=json.dumps(data), content_type="application/json")
        return r

    def _receive(self, data):
        r = self._save_order(data)
        self.assertTrue(r.json()["success"], r.json())
        self.invoice_id = r.json()["invoice_id"]
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))
        self.assertTrue(c.json()["success"], c.json())
        return self._invoice()

    def _invoice(self):
        return Invoice.objects.get(pk=self.invoice_id)

    def _roll(self, barcode):
        return WarehouseProductItem.objects.get(barcode=barcode)

    def _edit_url(self):
        return reverse("operating:warehouse_purchase_edit", args=[self.wh.pk, self.invoice_id])

    def _form(self, charges=None):
        loaded = self.client.get(self._edit_url(),
                                 headers={"x-requested-with": "XMLHttpRequest"}).json()
        form = {"warehouse_id": self.wh.pk, "current_account_id": loaded["current_account_id"],
                "unit": loaded["unit"], "date": self._invoice().date.isoformat(),
                "products": loaded["products"]}
        if charges is not None:
            form["charges"] = charges
        return form

    def _edit(self, form):
        return self.client.post(self._edit_url(), data=json.dumps(form),
                                content_type="application/json")

    def _balances(self):
        return {r["code"]: r["balance"] for r in balance_sheet(self.book)["trial_balance"]["rows"]}

    def _assert_shelves_match_the_ledger(self):
        self.assertTrue(balance_sheet(self.book)["balanced"])
        inventory = reconcile(self.book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])

    def _owed_to(self, account):
        account.refresh_from_db()
        return -account.cached_balance

    # ── an order ────────────────────────────────────────────────────
    def test_an_order_keeps_its_cost_and_owes_nothing_yet(self, _upload):
        r = self._save_order(self._payload([self._charge(30, reference="DGN-118")]))
        self.assertTrue(r.json()["success"], r.json())
        charge = PurchaseCharge.objects.get()
        self.assertEqual((charge.current_account, charge.amount, charge.reference),
                         (self.carrier, Decimal("30.00"), "DGN-118"))
        self.assertIsNone(charge.posted_movement)
        self.assertEqual(self._owed_to(self.carrier), 0)
        # The form opens with it.
        page = self.client.get(reverse("accounts:goods_receipt_edit", args=[r.json()["invoice_id"]]))
        self.assertContains(page, "DGN-118")

    # ── received ────────────────────────────────────────────────────
    def test_received_it_is_owed_to_the_carrier_and_inside_the_goods_cost(self, _upload):
        invoice = self._receive(self._payload([self._charge(30)]))
        self.assertEqual(invoice.total, Decimal("175.00"))           # Karven's bill is Karven's
        self.assertEqual(self._owed_to(self.karven), Decimal("175.00"))
        self.assertEqual(self._owed_to(self.carrier), Decimal("30.00"))
        mv = PurchaseCharge.objects.get().posted_movement
        self.assertEqual((mv.date, mv.movement_type), (invoice.posting_date, "invoice_purchase"))
        self.assertIn(invoice.display_number, mv.description)
        for barcode in ("KRV-A", "KRV-B"):                           # 30 / 50 m = 0.60 a meter
            roll = self._roll(barcode)
            self.assertEqual((roll.unit_cost_base, roll.charges_per_unit),
                             (Decimal("4.1000"), Decimal("0.6000")))
        self.assertEqual(self._balances()["1300"], Decimal("205.00"))
        self._assert_shelves_match_the_ledger()

    def test_the_purchase_page_shows_the_cost_with_delivery(self, _upload):
        """3.50 a meter + 0.60 of delivery: 4.10, and 205.00 for the 50 m."""
        invoice = self._receive(self._payload([self._charge(30)]))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[invoice.pk]))
        # In cents on the page, exact on hover.
        self.assertContains(page, "With delivery: $4.10 / m (+$0.60)")
        self.assertContains(page, 'data-exact="With delivery: $4.1000 / m (+$0.6000)"')
        # One card: Karven for the goods, Öz Turanlar for the delivery, added up.
        cost = page.context["cost"]
        self.assertEqual([(r["role"], r["account"], r["amount"]) for r in cost["rows"]],
                         [("supplier", self.karven, Decimal("175.00")),
                          ("carrier", self.carrier, Decimal("30.00"))])
        self.assertEqual(cost["total"], Decimal("205.00"))
        self.assertEqual(cost["base_parts"], [Decimal("175.00"), Decimal("30.00")])
        self.assertFalse(any(r["converted"] for r in cost["rows"]))
        self.assertContains(page, "$175.00 + $30.00 = $205.00")

    def test_without_a_delivery_cost_the_page_says_nothing_of_it(self, _upload):
        invoice = self._receive(self._payload())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[invoice.pk]))
        self.assertNotContains(page, "With delivery")
        # Just the supplier's row, with no total under it.
        self.assertEqual(len(page.context["cost"]["rows"]), 1)
        self.assertNotContains(page, 'class="po-cost-row po-cost-total"')

    def test_it_is_spread_by_each_lines_value(self, _upload):
        """175.00 of G07 and 70.00 of G08: of a 49.00 delivery, 35.00 and 14.00."""
        self._receive(self._payload(
            [self._charge(49)],
            extra_variant={"name": "G08", "sku": "K24644.G08", "price": "7.00", "currency": "USD",
                           "tops": [{"qty": 10, "barcode": "KRV-C"}]}))
        self.assertEqual(self._roll("KRV-A").charges_per_unit, Decimal("0.7000"))   # 35 / 50 m
        self.assertEqual(self._roll("KRV-C").charges_per_unit, Decimal("1.4000"))   # 14 / 10 m
        self.assertEqual(self._roll("KRV-C").unit_cost_base, Decimal("8.4000"))
        self._assert_shelves_match_the_ledger()

    def test_a_share_that_does_not_come_to_whole_cents_is_a_closing_difference(self, _upload):
        """10.00 over 51 m is 0.1961 a meter: the rolls carry 10.0011."""
        self._receive(self._payload([self._charge(10)], lengths=(30, 21)))
        self.assertEqual(self._owed_to(self.carrier), Decimal("10.00"))
        b = self._balances()
        self.assertEqual(b["1300"], Decimal("51") * Decimal("3.50") + Decimal("51") * Decimal("0.1961"))
        self._assert_shelves_match_the_ledger()

    def test_the_share_per_meter_is_rounded_half_up(self, _upload):
        """10.00 over 52 m is 0.19230…: carried as 0.1923, as an invoice line
        rounds — the rolls hold 9.9996 against 10.00 owed."""
        self._receive(self._payload([self._charge(10)], lengths=(30, 22)))
        self.assertEqual(self._roll("KRV-A").charges_per_unit, Decimal("0.1923"))
        self.assertEqual(self._owed_to(self.carrier), Decimal("10.00"))
        self.assertEqual(self._balances()["1300"],
                         Decimal("52") * Decimal("3.50") + Decimal("52") * Decimal("0.1923"))
        self._assert_shelves_match_the_ledger()

    def test_a_carrier_billing_in_lira_is_owed_lira_and_the_goods_take_dollars(self, _upload):
        """Öz Turanlar bills 1,200 TL; at 40 TL to the dollar that is 30.00,
        the same 0.60 a meter as a 30.00 bill in dollars."""
        tl = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.carrier.default_currency = tl
        self.carrier.save()

        def rate(src, dst, on_date=None):
            return Decimal("0.025") if (src, dst) == ("TRY", "USD") else Decimal("1")

        with patch("accounting.services.get_exchange_rate", side_effect=rate):
            invoice = self._receive(self._payload([self._charge(1200)]))
        mv = PurchaseCharge.objects.get().posted_movement
        self.assertEqual((mv.amount, mv.currency.code, mv.amount_base),
                         (Decimal("-1200.00"), "TRY", Decimal("-30.00")))
        self.assertEqual(mv.date, invoice.posting_date)       # the day the goods came in
        self.assertEqual(self._roll("KRV-A").charges_per_unit, Decimal("0.6000"))
        self.assertEqual(self._balances()["1300"], Decimal("205.00"))
        self._assert_shelves_match_the_ledger()
        # The form says what it is billed in.
        page = self.client.get(reverse("accounts:goods_receipt_edit", args=[self.invoice_id]))
        self.assertContains(page, '"currency": "TRY"')
        # The purchase page adds it up in dollars: the lira row says what
        # it came to and at what rate, and the sum is all in dollars.
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[self.invoice_id]))
        cost = page.context["cost"]
        carrier = cost["rows"][1]
        self.assertEqual((carrier["converted"], carrier["base"], carrier["rate"]),
                         (True, Decimal("30.00"), Decimal("0.025")))
        self.assertContains(page, "$30.00 <span class=\"r\">@ 0.025</span>", html=False)
        self.assertContains(page, "$175.00 + $30.00 = $205.00")

    def test_two_carriers_each_owed_their_own(self, _upload):
        porter = CurrentAccount.objects.create(
            book=self.book, code="C-HML", name="Hamal", type="supplier", default_currency=self.usd)
        self._receive(self._payload([self._charge(30), self._charge(5, porter, description="Unloading")]))
        self.assertEqual(self._owed_to(self.carrier), Decimal("30.00"))
        self.assertEqual(self._owed_to(porter), Decimal("5.00"))
        self.assertEqual(self._roll("KRV-A").charges_per_unit, Decimal("0.7000"))
        self._assert_shelves_match_the_ledger()

    # ── after some has left ─────────────────────────────────────────
    def test_a_cost_added_after_meters_left_puts_their_share_in_cost_of_goods(self, _upload):
        """10 m of KRV-A went out at 3.50. A 50.00 delivery is 1.00 a meter:
        those 10 m take 10.00 with them, the 40 m on the shelf keep 40.00."""
        self._receive(self._payload())
        roll = self._roll("KRV-A")
        r = self.client.post(
            reverse("operating:warehouse_roll_edit", args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": "20", "change_reason": "display"})
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(self._balances()["5110"], Decimal("35.00"))

        r = self._edit(self._form([self._charge(50)]))
        self.assertEqual(r.status_code, 200, r.content)

        b = self._balances()
        self.assertEqual(b["5110"], Decimal("45.00"))                # 10 m x 4.50
        self.assertEqual(b["1300"], Decimal("180.00"))               # 40 m x 4.50
        self.assertEqual(self._owed_to(self.carrier), Decimal("50.00"))
        self._assert_shelves_match_the_ledger()

    # ── edited ──────────────────────────────────────────────────────
    def test_a_changed_cost_replaces_its_share(self, _upload):
        self._receive(self._payload([self._charge(30)]))
        mv_id = PurchaseCharge.objects.get().posted_movement_id
        self.assertEqual(self._edit(self._form([self._charge(20)])).status_code, 200)
        self.assertEqual(self._roll("KRV-A").unit_cost_base, Decimal("3.9000"))
        self.assertEqual(self._owed_to(self.carrier), Decimal("20.00"))
        self.assertEqual(PurchaseCharge.objects.get().posted_movement_id, mv_id)   # in place
        self._assert_shelves_match_the_ledger()

    def test_a_corrected_price_keeps_the_share_on_top(self, _upload):
        self._receive(self._payload([self._charge(30)]))
        form = self._form()          # no "charges": the panel's save leaves them be
        form["products"][0]["variants"][0]["price"] = "4.00"
        self.assertEqual(self._edit(form).status_code, 200)
        self.assertEqual(self._roll("KRV-A").unit_cost_base, Decimal("4.6000"))
        self.assertEqual(PurchaseCharge.objects.count(), 1)
        self._assert_shelves_match_the_ledger()

    def test_a_removed_cost_takes_its_payable_and_share(self, _upload):
        self._receive(self._payload([self._charge(30)]))
        self.assertEqual(self._edit(self._form([])).status_code, 200)
        self.assertFalse(PurchaseCharge.objects.exists())
        self.assertEqual(self._owed_to(self.carrier), 0)
        self.assertEqual(self._roll("KRV-A").unit_cost_base, Decimal("3.5000"))
        self.assertEqual(self._balances()["1300"], Decimal("175.00"))
        self._assert_shelves_match_the_ledger()

    # ── undone, cancelled ───────────────────────────────────────────
    def test_undoing_the_receipt_owes_nothing_until_received_again(self, _upload):
        self._receive(self._payload([self._charge(30)]))
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[self.invoice_id]))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._owed_to(self.carrier), 0)
        self.assertIsNone(PurchaseCharge.objects.get().posted_movement)

        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))
        self.assertTrue(c.json()["success"], c.json())
        self.assertEqual(self._owed_to(self.carrier), Decimal("30.00"))
        self.assertEqual(self._roll("KRV-A").unit_cost_base, Decimal("4.1000"))
        self._assert_shelves_match_the_ledger()

    def test_cancelling_owes_nothing(self, _upload):
        self._receive(self._payload([self._charge(30)]))
        r = self.client.post(reverse("accounts:purchase_cancel", args=[self.invoice_id]),
                             data={"reason": "wrong delivery"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._owed_to(self.carrier), 0)
        self.assertTrue(balance_sheet(self.book)["balanced"])

    # ── refused ─────────────────────────────────────────────────────
    def test_a_cost_owed_in_another_book_is_refused(self, _upload):
        other = CurrentAccount.objects.create(
            book=Book.objects.create(name="Ergene"), code="C-X", name="Öz Turanlar",
            type="supplier", default_currency=self.usd)
        r = self._save_order(self._payload([self._charge(30, other)]))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Invoice.objects.exists())

    def test_a_cost_with_no_amount_is_refused(self, _upload):
        r = self._save_order(self._payload([self._charge("")]))
        self.assertEqual(r.status_code, 400)
