"""Correcting a received purchase keeps the ledger's stock equal to the shelves.

The purchase carries a correction to Inventory (1300) through its own
movement. Two things have to follow that for the books to stay right: the
stock on the shelves, and the cost of whatever had already left them.

Run with:
    python manage.py test accounting.tests.test_purchase_edit_ledger
"""
from decimal import Decimal

from django.urls import reverse

from accounting.services_ledger import balance_sheet, reconcile
from accounting.tests import test_received_purchase_edit as base


class PurchaseEditLedgerTest(base.TestCase):
    """The purchase: 30 m (KRV-A) and 20 m (KRV-B) at 3.50, 175.00 owed."""
    setUp = base.ReceivedPurchaseEditTest.setUp
    _invoice = base.ReceivedPurchaseEditTest._invoice
    _roll = base.ReceivedPurchaseEditTest._roll
    _edit_url = base.ReceivedPurchaseEditTest._edit_url
    _form = base.ReceivedPurchaseEditTest._form
    _variant = base.ReceivedPurchaseEditTest._variant
    _save = base.ReceivedPurchaseEditTest._save

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def _assert_shelves_match_the_ledger(self):
        self.assertTrue(balance_sheet(self.book)["balanced"])
        inventory = reconcile(self.book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])

    def _take_out(self, barcode, new_length, reason):
        roll = self._roll(barcode)
        r = self.client.post(
            reverse("operating:warehouse_roll_edit", args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": str(new_length), "change_reason": reason})
        self.assertTrue(r.json()["success"], r.json())

    def _reprice(self, price):
        form = self._form()
        self._variant(form)["price"] = price
        r = self._save(form)
        self.assertEqual(r.status_code, 200, r.content)

    # ── a price that does not come to whole cents ────────────────
    def test_a_fraction_of_a_cent_between_the_bill_and_the_rolls_is_a_closing_difference(self):
        """50 m at 3.4555 is 172.775. The supplier is owed whole cents; the
        rolls are carried at what they cost. The half cent between the two
        belongs to neither, and Inventory holds what the shelves do."""
        self._reprice("3.4555")

        owed = self._invoice().total
        self.assertIn(owed, (Decimal("172.77"), Decimal("172.78")))
        b = self._balances()
        self.assertEqual(b["1200"], -owed)                    # the supplier's account, to the cent
        self.assertEqual(b["1300"], Decimal("172.775"))
        self.assertEqual(b.get("5150", 0) - b.get("4950", 0), owed - Decimal("172.775"))
        self._assert_shelves_match_the_ledger()

    # ── a length corrected on the purchase ───────────────────────
    def test_a_roll_re_measured_on_the_purchase_moves_stock_and_debt_together(self):
        form = self._form()
        self._variant(form)["tops"][1]["qty"] = "18"          # KRV-B, 20 → 18
        self.assertEqual(self._save(form).status_code, 200)

        self.assertEqual(self._invoice().total, Decimal("168.00"))
        b = self._balances()
        self.assertEqual(b["1300"], Decimal("168.00"))
        self.assertFalse(b.get("5120"))                       # the supplier's, not ours
        self._assert_shelves_match_the_ledger()

    # ── a price corrected after goods have left ──────────────────
    def test_a_corrected_price_re_costs_what_has_already_left(self):
        """10 m went out at 3.50. The price turns out to have been 4.00:
        those 10 m cost 40.00, not 35.00, and the 5.00 between must not be
        left sitting in stock."""
        self._take_out("KRV-A", 20, "display")                # 10 m out → 5110
        self.assertEqual(self._balances()["5110"], Decimal("35.00"))

        self._reprice("4.00")

        self.assertEqual(self._invoice().total, Decimal("200.00"))    # 50 m x 4.00
        b = self._balances()
        self.assertEqual(b["5110"], Decimal("40.00"))                 # 10 m x 4.00
        self.assertEqual(b["1300"], Decimal("160.00"))                # 40 m left x 4.00
        self._assert_shelves_match_the_ledger()

    def test_a_lower_price_brings_the_cost_down_the_same_way(self):
        self._take_out("KRV-A", 20, "loss")                   # 10 m out → 5120

        self._reprice("3.00")

        b = self._balances()
        self.assertEqual(b["5120"], Decimal("30.00"))
        self.assertEqual(b["1300"], Decimal("120.00"))                # 40 m x 3.00
        self._assert_shelves_match_the_ledger()

    def test_re_pricing_leaves_one_entry_per_movement(self):
        """Re-posting replaces an entry; it must not add a second."""
        from accounting.models_ledger import JournalEntry
        self._take_out("KRV-A", 20, "display")
        before = JournalEntry.objects.count()

        self._reprice("4.00")
        self._reprice("4.25")

        self.assertEqual(JournalEntry.objects.count(), before)
        self.assertEqual(self._balances()["5110"], Decimal("42.50"))

    def test_the_purchases_own_entry_is_corrected_in_place(self):
        """One entry for the purchase before and after, at the new figure
        and still on the purchase's own date."""
        from django.contrib.contenttypes.models import ContentType
        from accounting.models_ledger import JournalEntry
        movement = self._invoice().posted_movement
        ct = ContentType.objects.get_for_model(movement.__class__)

        self._reprice("4.00")

        entry = JournalEntry.objects.get(source_type=ct, source_id=movement.pk)
        self.assertEqual(str(entry.date), "2026-08-21")
        self.assertEqual(entry.lines.get(account__code="1300").debit, Decimal("200.00"))
        self.assertEqual(self._invoice().posted_movement.amount, Decimal("-200.00"))
        self.assertEqual(self._balances()["1300"], Decimal("200.00"))
        self._assert_shelves_match_the_ledger()

    def test_a_save_that_changes_no_price_re_posts_nothing(self):
        """The purchase's own entry is refreshed on every save, as it always
        was; the entries of what left its rolls are not touched."""
        from accounting.models_ledger import JournalEntry
        self._take_out("KRV-A", 20, "display")
        cost_entries = JournalEntry.objects.filter(lines__account__code="5110")
        ids = set(cost_entries.values_list("pk", flat=True))
        self.assertEqual(len(ids), 1)

        self.assertEqual(self._save(self._form()).status_code, 200)

        self.assertEqual(set(cost_entries.values_list("pk", flat=True)), ids)
        self.assertEqual(self._balances()["5110"], Decimal("35.00"))


class ReceivedAtAFractionalPriceTest(base.TestCase):
    """The same fraction, on the day the goods arrive: 61.20 m at 3.4555
    is 211.4766, billed in whole cents."""

    def test_stock_is_carried_at_cost_from_the_moment_it_is_received(self):
        import json
        from unittest.mock import patch

        from django.contrib.auth import get_user_model

        from accounting.models import Book, CurrencyCategory
        from accounting.models_accounts import CurrentAccount, Invoice
        from operating.models import Warehouse

        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        karven = CurrentAccount.objects.create(
            book=book, code="C-KRV", name="Karven", type="supplier",
            default_currency=usd)
        wh = Warehouse.objects.create(name="Fabrika", accounting_book=book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="fraction", password="pw", email="f@e.t"))

        with patch("marketing.utils.bunny_storage.upload_to_bunny",
                   return_value="https://mock-cdn.net/qr.png"):
            order = self.client.post(
                reverse("accounts:purchase_order_save", kwargs={"book_id": book.pk}),
                data=json.dumps({
                    "warehouse_id": wh.pk, "current_account_id": karven.pk,
                    "unit": "mt", "date": "2026-08-21", "delivery_date": "2026-09-01",
                    "products": [{
                        "main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                        "has_variants": True,
                        "variants": [{"name": "G07", "sku": "K24644.G07",
                                      "price": "3.4555", "currency": "USD",
                                      "tops": [{"qty": "61.2", "barcode": "KRV-F"}]}],
                    }],
                }), content_type="application/json")
            invoice_id = order.json()["invoice_id"]
            confirm = self.client.post(
                reverse("accounts:purchase_order_confirm", args=[invoice_id]))
        self.assertTrue(confirm.json()["success"], confirm.json())

        owed = Invoice.objects.get(pk=invoice_id).total
        self.assertEqual(owed, Decimal("211.48"))
        b = {r["code"]: r["balance"] for r in
             balance_sheet(book)["trial_balance"]["rows"]}
        self.assertEqual(b["1200"], Decimal("-211.48"))
        self.assertEqual(b["1300"], Decimal("211.4766"))
        self.assertEqual(b["5150"], Decimal("0.0034"))
        inventory = reconcile(book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])
        self.assertTrue(balance_sheet(book)["balanced"])
