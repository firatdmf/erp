"""Each current account movement gets the other half it never had.

Run with:
    python manage.py test accounting.test_posting
"""
from decimal import Decimal

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.models_ledger import ChartAccount, JournalEntry
from accounting.services_ledger import balance_sheet, ensure_chart
from accounting.services_posting import (NoRuleFor, lines_for_movement,
                                         post_movement, reclassify_payables)


class PostingRules(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.current_account = CurrentAccount.objects.create(
            book=self.book, code="00554", name="OLEG", default_currency=self.usd)

    def _mv(self, kind, amount, date="2026-07-01"):
        mv = CurrentAccountMovement.objects.create(
            current_account=self.current_account, book=self.book, date=date,
            amount=Decimal(amount), currency=self.usd,
            movement_type=kind, description=kind)
        self.current_account.recompute_balance(save=True)
        return mv

    def _balances(self):
        return {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}

    def test_an_opening_balance_gets_equity_as_its_contra(self):
        """Not revenue: a balance carried in is a prior year's trading."""
        post_movement(self._mv("opening", "1000.00"))
        b = self._balances()
        self.assertEqual(b["1200"], Decimal("1000.00"))
        self.assertEqual(b["3100"], Decimal("1000.00"))
        self.assertNotIn("4000", b)

    def test_a_sale_gets_revenue(self):
        post_movement(self._mv("order_sale", "167.75"))
        b = self._balances()
        self.assertEqual(b["1200"], Decimal("167.75"))
        self.assertEqual(b["4000"], Decimal("167.75"))

    def test_a_collection_moves_the_debt_into_cash(self):
        post_movement(self._mv("opening", "1000.00"))
        post_movement(self._mv("collection", "-400.00"))
        b = self._balances()
        self.assertEqual(b["1000"], Decimal("400.00"))
        self.assertEqual(b["1200"], Decimal("600.00"))

    def test_the_direction_comes_from_the_sign_not_the_table(self):
        """The rule table names an account and never a side, because the
        side is the part that is easy to get backwards."""
        out = lines_for_movement(self._mv("opening", "-250.00"))
        control = next(l for l in out if l["code"] == "1200")
        contra = next(l for l in out if l["code"] == "3100")
        self.assertEqual(control["credit"], Decimal("250.00"))
        self.assertEqual(contra["debit"], Decimal("250.00"))

    def test_the_current_account_is_carried_onto_the_control_leg(self):
        entry = post_movement(self._mv("order_sale", "10.00"))
        self.assertEqual(entry.lines.get(account__code="1200").current_account, self.current_account)

    def test_a_zero_movement_posts_nothing(self):
        self.assertIsNone(post_movement(self._mv("invoice_sale", "0.00")))
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_an_undecided_type_is_refused_not_guessed_at(self):
        """103 adjustments sit on Laleli and they are not one thing. A
        movement posted to the wrong account is worse than one not posted,
        because it looks finished."""
        with self.assertRaises(NoRuleFor):
            post_movement(self._mv("adjustment", "500.00"))
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_every_entry_balances_whatever_the_type(self):
        for kind in ("opening", "order_sale", "collection", "interest",
                     "check_in", "invoice_purchase"):
            post_movement(self._mv(kind, "123.45"))
            post_movement(self._mv(kind, "-67.89"))
        tb = balance_sheet(self.book)["trial_balance"]
        self.assertEqual(tb["total_debit"], tb["total_credit"])
        self.assertTrue(tb["balanced"])


class CreditBalancesBecomePayables(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        ensure_chart()
        self.usd = usd

    def _current_account(self, code, amount):
        c = CurrentAccount.objects.create(
            book=self.book, code=code, name=code, default_currency=self.usd)
        mv = CurrentAccountMovement.objects.create(
            current_account=c, book=self.book, date="2026-07-01", amount=Decimal(amount),
            currency=self.usd, movement_type="opening", description="ob")
        c.recompute_balance(save=True)
        post_movement(mv)
        return c

    def test_a_book_that_owes_reports_a_payable_not_a_negative_asset(self):
        self._current_account("A", "1000.00")
        self._current_account("B", "-250.00")
        entry, n = reclassify_payables(self.book, date="2026-09-03")
        self.assertEqual(n, 1)
        b = {r["code"]: r["balance"]
             for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(b["1200"], Decimal("1000.00"))
        self.assertEqual(b["2000"], Decimal("250.00"))

    def test_it_does_nothing_when_no_account_is_in_credit(self):
        self._current_account("A", "1000.00")
        entry, n = reclassify_payables(self.book, date="2026-09-03")
        self.assertIsNone(entry)
        self.assertEqual(n, 0)

    def test_the_equation_still_holds_afterwards(self):
        self._current_account("A", "1000.00")
        self._current_account("B", "-250.00")
        reclassify_payables(self.book, date="2026-09-03")
        gl = balance_sheet(self.book)
        self.assertTrue(gl["balanced"])
        self.assertEqual(gl["assets"], gl["liabilities_plus_equity"])


class TheBackfillCommand(TestCase):
    """Ergene's shape in miniature: opening balances, a sale, a collection,
    stock on the floor, and one account in credit."""

    def setUp(self):
        from io import StringIO
        from operating.models import (Warehouse, WarehouseProduct,
                                      WarehouseProductItem)
        self.StringIO = StringIO
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.usd = usd
        ensure_chart()

        owing = CurrentAccount.objects.create(
            book=self.book, code="A", name="A", default_currency=usd)
        owed = CurrentAccount.objects.create(
            book=self.book, code="B", name="B", default_currency=usd)
        for current_account, kind, amt in ((owing, "opening", "1000.00"),
                                (owing, "order_sale", "200.00"),
                                (owing, "collection", "-300.00"),
                                (owed, "opening", "-150.00")):
            CurrentAccountMovement.objects.create(
                current_account=current_account, book=self.book, date="2026-07-01",
                amount=Decimal(amt), currency=usd, movement_type=kind,
                description=kind)
        for c in (owing, owed):
            c.recompute_balance(save=True)

        wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="seta", sku="S1", quantity=Decimal("0"),
            cost_usd=Decimal("4.00"))
        WarehouseProductItem.objects.create(
            product=wp, meters=Decimal("100"), meters_remaining=Decimal("100"),
            barcode="BC-1", status="in_stock", unit_cost_base=Decimal("4.00"))

    def _run(self, *args):
        from django.core.management import call_command
        out = self.StringIO()
        call_command("backfill_ledger", "--book", str(self.book.pk),
                     *args, stdout=out)
        return out.getvalue()

    def test_a_dry_run_writes_nothing(self):
        self._run()
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_applying_makes_the_equation_hold(self):
        self._run("--apply")
        gl = balance_sheet(self.book)
        self.assertTrue(gl["balanced"])
        self.assertEqual(gl["assets"], gl["liabilities_plus_equity"])

    def test_it_posts_the_stock_at_what_the_items_cost(self):
        self._run("--apply")
        b = {r["code"]: r["balance"]
             for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(b["1300"], Decimal("400.00"))     # 100m x 4.00

    def test_running_it_twice_does_not_double_post(self):
        """A run that stopped halfway has to be safe to repeat."""
        self._run("--apply")
        first = balance_sheet(self.book)["assets"]
        entries = JournalEntry.objects.count()
        self._run("--apply")
        self.assertEqual(balance_sheet(self.book)["assets"], first)
        # Nothing at all is re-posted: movements dedupe on their source
        # row, inventory and the reclass on the batch reference.
        self.assertEqual(JournalEntry.objects.count(), entries)

    def test_the_batch_reference_can_undo_the_run(self):
        self._run("--apply")
        ref = f"LEDGER-BF-{self.book.pk}"
        self.assertTrue(JournalEntry.objects.filter(reference=ref).exists())
        JournalEntry.objects.filter(reference=ref).delete()
        self.assertEqual(balance_sheet(self.book)["assets"], Decimal("0.00"))
