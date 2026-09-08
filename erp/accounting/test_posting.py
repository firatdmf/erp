"""Each current account movement gets the other half it never had.

Run with:
    python manage.py test accounting.test_posting
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
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
            product=wp, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
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


class CashEventsGetTheirContra(TestCase):
    """A dividend, a capital injection and an expense move cash without any
    current account being involved, so the cash journal is the source."""

    def setUp(self):
        from accounting.models import CashAccount
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd)
        # EquityCapital insists on knowing whose money it was.
        self.member = get_user_model().objects.create_user(
            "owner", password="pw").member

    def _equity(self, model_name, amount, positive):
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType

        from accounting.models import CashTransactionEntry
        M = apps.get_model("accounting", model_name)
        # The equity models do not share a field vocabulary: a capital
        # injection has date_invested and a note, a dividend has date and a
        # description.
        names = {f.name for f in M._meta.local_fields}
        extra = {}
        extra["date" if "date" in names else "date_invested"] = "2026-09-03"
        if "description" in names:
            extra["description"] = f"{model_name} row"
        elif "note" in names:
            extra["note"] = f"{model_name} row"
        if "member" in names:
            extra["member"] = self.member
        obj = M.objects.create(
            book=self.book, cash_account=self.cash, currency=self.usd,
            amount=Decimal(amount), **extra)
        return CashTransactionEntry.objects.create(
            book=self.book, content_type=ContentType.objects.get_for_model(M),
            content_pk=obj.pk, amount=Decimal(amount),
            is_amount_positive=positive, currency=self.usd,
            cash_account=self.cash, date="2026-09-03")

    def _balances(self):
        return {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}

    def test_a_dividend_takes_cash_out_of_equity(self):
        from accounting.services_posting import post_cash_entry
        post_cash_entry(self._equity("EquityDivident", "1500.00", False))
        b = self._balances()
        # 3300 is equity, so its balance reads credit-minus-debit. A
        # dividend DEBITS it, which is exactly what a contra-equity account
        # should look like: it reduces equity rather than adding to it.
        self.assertEqual(b["3300"], Decimal("-1500.00"))
        self.assertEqual(b["1000"], Decimal("-1500.00"))  # cash went out
        self.assertEqual(balance_sheet(self.book)["equity"], Decimal("-1500.00"))

    def test_capital_put_in_is_not_revenue(self):
        from accounting.services_posting import post_cash_entry
        post_cash_entry(self._equity("EquityCapital", "5000.00", True))
        b = self._balances()
        self.assertEqual(b["3000"], Decimal("5000.00"))
        self.assertNotIn("4000", b)

    def test_a_payment_is_refused_because_its_movement_carries_it(self):
        """Posting the cash row too would book the payment twice, and each
        entry would balance on its own, so nothing would catch it."""
        from accounting.services_posting import NoRuleFor, lines_for_cash_entry
        with self.assertRaises(NoRuleFor):
            lines_for_cash_entry(object(), "payment")

    def test_a_transfer_is_refused_because_both_legs_are_cash(self):
        from accounting.services_posting import NoRuleFor, lines_for_cash_entry
        with self.assertRaises(NoRuleFor):
            lines_for_cash_entry(object(), "currencyexchange")

    def test_the_entry_still_balances(self):
        from accounting.services_posting import post_cash_entry
        post_cash_entry(self._equity("EquityDivident", "1500.00", False))
        post_cash_entry(self._equity("EquityCapital", "5000.00", True))
        tb = balance_sheet(self.book)["trial_balance"]
        self.assertEqual(tb["total_debit"], tb["total_credit"])
        self.assertTrue(balance_sheet(self.book)["balanced"])


class ClosingThePeriod(TestCase):
    """Temporary accounts are emptied into Retained Earnings.

    Without it 4000 would hold every year's sales at once and 3300 every
    year's distributions, and nothing on the page could say which year
    either belonged to.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()

    def _post(self, lines, when="2026-06-30"):
        from accounting.services_ledger import post_entry
        return post_entry(book=self.book, date=when, description="x", lines=lines)

    def _b(self, date_to=None):
        return {r["code"]: r["balance"]
                for r in balance_sheet(self.book, date_to=date_to)
                ["trial_balance"]["rows"]}

    def _trade(self, sales="1000.00", expense="400.00", dividend=None):
        from accounting.services_ledger import credit, debit
        self._post([debit("1200", sales), credit("4000", sales)])
        if expense:
            self._post([debit("5100", expense), credit("1000", expense)])
        if dividend:
            self._post([debit("3300", dividend), credit("1000", dividend)])

    def test_it_empties_revenue_expenses_and_dividends(self):
        from accounting.services_posting import close_period
        self._trade(dividend="200.00")
        close_period(self.book, date_to="2026-12-31")
        b = self._b()
        for code in ("4000", "5100", "3300"):
            self.assertEqual(b.get(code, Decimal("0")), Decimal("0.00"), code)

    def test_what_was_kept_lands_in_retained_earnings(self):
        from accounting.services_posting import close_period
        self._trade(sales="1000.00", expense="400.00", dividend="200.00")
        close_period(self.book, date_to="2026-12-31")
        # 1000 earned, 400 spent, 200 paid out -> 400 kept.
        self.assertEqual(self._b()["3200"], Decimal("400.00"))

    def test_equity_does_not_move(self):
        """A close relocates the result; it must never change it."""
        from accounting.services_posting import close_period
        self._trade(dividend="200.00")
        before = balance_sheet(self.book)["equity"]
        close_period(self.book, date_to="2026-12-31")
        self.assertEqual(balance_sheet(self.book)["equity"], before)

    def test_the_books_still_balance(self):
        from accounting.services_posting import close_period
        self._trade(dividend="200.00")
        close_period(self.book, date_to="2026-12-31")
        gl = balance_sheet(self.book)
        self.assertTrue(gl["balanced"])
        self.assertEqual(gl["assets"], gl["liabilities_plus_equity"])

    def test_a_loss_takes_retained_earnings_down(self):
        from accounting.services_posting import close_period
        self._trade(sales="100.00", expense="450.00")
        close_period(self.book, date_to="2026-12-31")
        self.assertEqual(self._b()["3200"], Decimal("-350.00"))

    def test_permanent_accounts_are_left_alone(self):
        from accounting.services_posting import close_period
        self._trade()
        before = self._b()
        close_period(self.book, date_to="2026-12-31")
        after = self._b()
        for code in ("1200", "1000"):
            self.assertEqual(after[code], before[code], code)

    def test_a_second_year_closes_only_its_own_trading(self):
        """The point of the whole exercise: year two must not restate year
        one. The entry zeroes each account, so the next close only ever
        sees what accumulated since."""
        from accounting.services_posting import close_period
        self._trade(sales="1000.00", expense="400.00", dividend="200.00")
        close_period(self.book, date_to="2026-12-31")

        self._post_year_two()
        entry, balances = close_period(self.book, date_to="2027-12-31")
        # Year two earned 500 and spent nothing.
        self.assertEqual(balances["4000"], Decimal("-500.00"))
        self.assertEqual(self._b()["3200"], Decimal("900.00"))   # 400 + 500

    def _post_year_two(self):
        from accounting.services_ledger import credit, debit
        self._post([debit("1200", "500.00"), credit("4000", "500.00")],
                   when="2027-06-30")

    def test_closing_an_empty_period_does_nothing(self):
        from accounting.services_posting import close_period
        entry, balances = close_period(self.book, date_to="2026-12-31")
        self.assertIsNone(entry)
        self.assertEqual(balances, {})

    def test_closing_twice_over_the_same_period_is_a_no_op(self):
        from accounting.services_posting import close_period
        self._trade()
        close_period(self.book, date_to="2026-12-31")
        kept = self._b()["3200"]
        entry, _ = close_period(self.book, date_to="2026-12-31")
        self.assertIsNone(entry)
        self.assertEqual(self._b()["3200"], kept)
