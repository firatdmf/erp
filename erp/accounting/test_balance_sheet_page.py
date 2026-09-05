"""The accounting equation, on a page, both ways.

Run with:
    python manage.py test accounting.test_balance_sheet_page
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement
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
        cari = CariAccount.objects.create(
            book=self.book, code="00554", name="GÜRHAN", default_currency=self.usd)
        CariMovement.objects.create(
            cari=cari, book=self.book, date="2026-07-16",
            amount=Decimal("1000.00"), currency=self.usd,
            movement_type="opening", description="Carried forward")
        cari.recompute_balance()

    def _page(self):
        r = self.client.get(reverse("accounts:report_balance_sheet",
                                    kwargs={"book_id": self.book.pk}))
        self.assertEqual(r.status_code, 200)
        return r

    def test_the_page_renders(self):
        self.assertContains(self._page(), "Balance Sheet")

    def test_the_ledger_side_balances_even_when_empty(self):
        ctx = self._page().context
        self.assertTrue(ctx["gl"]["balanced"])
        self.assertEqual(ctx["gl"]["assets"], Decimal("0.00"))

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

    def test_posting_the_contra_moves_the_ledger_column(self):
        """What the migration will look like: post the opening equity and
        the ledger column starts agreeing with the subsidiary one."""
        post_entry(book=self.book, date="2026-07-16",
                   description="Opening balances carried forward",
                   lines=[debit("1200", "1000.00"), credit("3100", "1000.00")],
                   reference="OPENING-BACKFILL")
        ctx = self._page().context
        self.assertTrue(ctx["gl"]["balanced"])
        self.assertEqual(ctx["gl"]["assets"], Decimal("1000.00"))
        self.assertEqual(ctx["gl"]["equity"], Decimal("1000.00"))
        self.assertEqual(ctx["coverage"], Decimal("100.0"))

    def test_coverage_reports_how_much_is_posted(self):
        self.assertEqual(self._page().context["coverage"], Decimal("0.0"))

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
        ctx = self._page().context
        self.assertEqual(ctx["gl"]["liabilities_plus_equity"], Decimal("328646.42"))
        self.assertEqual(ctx["gl"]["assets"], ctx["gl"]["liabilities_plus_equity"])
        self.assertContains(self._page(), "328,646.42")

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

        cari = CariAccount.objects.get(code="00554")
        before = subsidiary_equation(self.book)

        expense = EquityExpense.objects.create(
            book=self.book, currency=self.usd, amount=Decimal("100.00"),
            date="2026-08-01", description="Electricity settled by the customer",
            paid_by_cari=cari,
            category=ExpenseCategory.objects.create(name="Utilities"))
        CariMovement.objects.create(
            cari=cari, book=self.book, date="2026-08-01",
            amount=Decimal("-100.00"), currency=self.usd,
            movement_type="adjustment", description="Paid our electricity",
            source_type=ContentType.objects.get_for_model(EquityExpense),
            source_id=expense.pk)
        cari.recompute_balance()

        after = subsidiary_equation(self.book)
        # The receivable fell by 100 and equity fell by 100 — the pair is
        # neutral, so the residual is exactly where it was.
        self.assertEqual(after["receivable"], before["receivable"] - Decimal("100.00"))
        self.assertEqual(after["equity"], before["equity"] - Decimal("100.00"))
        self.assertEqual(after["residual"], before["residual"])
        self.assertEqual(after["equity_from_cari"], Decimal("-100.00"))
        # And the causes still account for the residual exactly.
        self.assertEqual(after["causes_total"], after["residual"])
