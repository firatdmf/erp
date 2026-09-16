"""The accounting equation, on a page, both ways.

Run with:
    python manage.py test accounting.test_balance_sheet_page
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_ledger import credit, debit, ensure_chart, post_entry


class BalanceSheetPage(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        ensure_chart()
        self.user = get_user_model().objects.create_user(username="acct", password="pw")
        m = self.user.member
        m.books.set([self.book])
        m.default_book = self.book
        m.save(update_fields=["default_book"])
        self.client.force_login(self.user)

        # A receivable in the subsidiary ledger with no contra anywhere —
        # exactly the shape the legacy import left behind.
        current_account = CurrentAccount.objects.create(
            book=self.book, code="00554", name="GÜRHAN", default_currency=self.usd)
        CurrentAccountMovement.objects.create(
            current_account=current_account, book=self.book, date="2026-07-16",
            amount=Decimal("1000.00"), currency=self.usd,
            movement_type="opening", description="Carried forward")
        current_account.recompute_balance()

    def _page(self):
        r = self.client.get(reverse("accounts:report_balance_sheet",
                                    kwargs={"book_id": self.book.pk}))
        self.assertEqual(r.status_code, 200)
        return r

    def test_the_page_renders(self):
        self.assertContains(self._page(), "Balance Sheet")

    def test_the_ledger_side_balances_when_empty(self):
        """A book nothing has happened on reports zero on both sides,
        rather than failing to render for want of any rows to total."""
        empty = Book.objects.create(name="Empty Fabric", base_currency=self.usd)
        m = self.user.member
        m.books.add(empty)
        r = self.client.get(reverse("accounts:report_balance_sheet",
                                    kwargs={"book_id": empty.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["gl"]["balanced"])
        self.assertEqual(r.context["gl"]["assets"], Decimal("0.00"))

    def test_the_movement_reached_the_ledger_without_anyone_running_a_batch(self):
        """The opening balance in setUp is created the way every path
        creates one — CurrentAccountMovement.objects.create — and nothing
        else is done to it. It is on the ledger because saving it put it
        there."""
        ctx = self._page().context
        self.assertTrue(ctx["gl"]["balanced"])
        self.assertEqual(ctx["gl"]["assets"], Decimal("1000.00"))
        self.assertEqual(ctx["gl"]["equity"], Decimal("1000.00"))

    def test_the_subsidiary_side_reports_the_receivable_and_does_not_balance(self):
        ctx = self._page().context
        self.assertEqual(ctx["subs"]["receivable"], Decimal("1000.00"))
        self.assertFalse(ctx["subs"]["balanced"])
        self.assertEqual(ctx["subs"]["residual"], Decimal("1000.00"))

    def test_the_residual_is_accounted_for_exactly(self):
        """The causes are an identity, not an estimate — if they ever stop
        summing to the residual, something is unexplained and the page has
        to say so rather than round it away."""
        ctx = self._page().context
        self.assertTrue(ctx["identity_holds"])
        self.assertEqual(ctx["subs"]["causes_total"], ctx["subs"]["residual"])

    def test_the_two_columns_agree_once_the_contra_is_posted(self):
        """The migration finishes when the ledger column and the
        subsidiary one report the same assets. For an opening balance that
        now happens as the movement is saved, so the page reaches 100%
        coverage with nobody having posted anything by hand."""
        ctx = self._page().context
        self.assertEqual(ctx["gl"]["assets"], ctx["subs"]["assets"])
        self.assertEqual(ctx["coverage"], Decimal("100.0"))

    def test_coverage_reports_how_much_is_posted(self):
        """A book whose movements are all posted reads 100; one with stock
        the ledger has not been told about reads lower, because the
        subsidiary column counts the stock and the ledger column does
        not."""
        self.assertEqual(self._page().context["coverage"], Decimal("100.0"))

        from operating.models import (Warehouse, WarehouseProduct,
                                      WarehouseProductItem)
        wh = Warehouse.objects.create(name="Laleli Depo",
                                      accounting_book=self.book)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="seta", sku="S1", quantity=Decimal("0"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("100"),
            quantity_remaining=Decimal("100"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4.00"))
        self.assertEqual(self._page().context["coverage"], Decimal("71.4"))

    def test_the_page_shows_each_control_account_against_its_ledger(self):
        """The two columns say whether the ledger has caught up. This says
        where it has not, which is the difference between a number to worry
        about and a job to do."""
        r = self._page()
        self.assertContains(r, "Control accounts")
        rec = r.context["rec"]
        receivables = rec["rows"][0]
        self.assertEqual(receivables["ledger"], Decimal("1000.00"))
        self.assertEqual(receivables["subsidiary"], Decimal("1000.00"))
        self.assertTrue(receivables["reconciled"])

    def test_an_adjustment_shows_up_as_held_rather_than_vanishing(self):
        CurrentAccountMovement.objects.create(
            current_account=CurrentAccount.objects.get(code="00554"),
            book=self.book, date="2026-07-16", amount=Decimal("120.00"),
            currency=self.usd, movement_type="adjustment",
            description="import correction")
        r = self._page()
        self.assertContains(r, "Held until somebody says what it was")
        pending = {p["code"]: p["balance"] for p in r.context["rec"]["pending"]}
        self.assertEqual(pending["1900"], Decimal("-120.00"))

    def test_a_book_you_are_not_assigned_is_refused(self):
        other = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        r = self.client.get(reverse("accounts:report_balance_sheet",
                                    kwargs={"book_id": other.pk}))
        self.assertEqual(r.status_code, 404)

    def test_the_grand_total_keeps_its_cents(self):
        """Django's `add` filter coerces Decimals through int(), which
        rendered a balanced 329,496.42 as 329,496.00 — a sound statement
        looking broken by 42 cents. The total is computed in Python."""
        post_entry(book=self.book, date="2026-07-16", description="Opening",
                   lines=[debit("1200", "328646.42"), credit("3100", "328646.42")])
        # Plus the 1,000.00 opening movement from setUp, which posted itself.
        ctx = self._page().context
        self.assertEqual(ctx["gl"]["liabilities_plus_equity"], Decimal("329646.42"))
        self.assertEqual(ctx["gl"]["assets"], ctx["gl"]["liabilities_plus_equity"])
        self.assertContains(self._page(), "329,646.42")

    def test_an_expense_a_customer_pays_counts_on_both_sides(self):
        """A client settling an expense on the book's behalf moves no cash:
        it debits the expense and credits what they owe. Both legs are real
        and both are already recorded, so it must not inflate the residual.

        Taking equity from the cash journal alone counted the receivable
        going down and missed the expense going up — worth $937.19 on the
        live Laleli book."""
        from accounting.models import EquityExpense, ExpenseCategory
        from accounting.services_ledger import subsidiary_equation
        from django.contrib.contenttypes.models import ContentType

        current_account = CurrentAccount.objects.get(code="00554")
        before = subsidiary_equation(self.book)

        expense = EquityExpense.objects.create(
            book=self.book, currency=self.usd, amount=Decimal("100.00"),
            date="2026-08-01", description="Electricity settled by the customer",
            paid_by_current_account=current_account,
            category=ExpenseCategory.objects.create(name="Utilities"))
        CurrentAccountMovement.objects.create(
            current_account=current_account, book=self.book, date="2026-08-01",
            amount=Decimal("-100.00"), currency=self.usd,
            movement_type="adjustment", description="Paid our electricity",
            source_type=ContentType.objects.get_for_model(EquityExpense),
            source_id=expense.pk)
        current_account.recompute_balance()

        after = subsidiary_equation(self.book)
        # The receivable fell by 100 and equity fell by 100 — the pair is
        # neutral, so the residual is exactly where it was.
        self.assertEqual(after["receivable"], before["receivable"] - Decimal("100.00"))
        self.assertEqual(after["equity"], before["equity"] - Decimal("100.00"))
        self.assertEqual(after["residual"], before["residual"])
        self.assertEqual(after["equity_from_current_account"], Decimal("-100.00"))
        # And the causes still account for the residual exactly.
        self.assertEqual(after["causes_total"], after["residual"])
