"""One ledger account, and every entry behind its balance.

Run with:
    python manage.py test accounting.tests.test_ledger_account_page
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_ledger import ensure_chart
from accounting.views_report import LedgerAccount


class LedgerAccountPage(TestCase):
    """The balance sheet printed a figure per account and nothing said what
    it was made of — least of all the entries that are on nobody's
    statement, like the re-split that keeps Accounts Payable in step."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.other = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        ensure_chart()
        self.tatyana = CurrentAccount.objects.create(
            book=self.book, code="ACC-050", name="TATYANA", type="customer", default_currency=self.usd)
        user = get_user_model().objects.create_superuser("owner", "o@x.com", "pw")
        user.member.books.set([self.book, self.other])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

    def _move(self, account, amount, kind="opening", when="2026-09-03", text=""):
        with self.captureOnCommitCallbacks(execute=True):
            return CurrentAccountMovement.objects.create(
                current_account=account, book=account.book, movement_type=kind, date=when,
                amount=Decimal(amount), amount_base=Decimal(amount), currency=self.usd, description=text)

    def _page(self, code, book=None, **params):
        return self.client.get(reverse("accounts:report_ledger_account",
                                       args=[(book or self.book).pk, code]), params)

    def test_it_lists_the_entries_with_a_running_balance(self):
        self._move(self.tatyana, "1000.00", text="carried over")
        self._move(self.tatyana, "250.00", kind="invoice_sale", when="2026-09-10", text="a sale")
        r = self._page("1200")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([row["balance"] for row in r.context["rows"]],
                         [Decimal("1000.00"), Decimal("1250.00")])
        self.assertEqual(r.context["closing"], Decimal("1250.00"))
        self.assertContains(r, "Accounts Receivable (1200)")
        self.assertContains(r, "against Sales (4000)")
        self.assertContains(r, "ACC-050")           # the party, linked to its statement

    def test_the_payables_resplit_is_visible_here(self):
        self._move(self.tatyana, "-529.66")
        r = self._page("2000")
        self.assertEqual(r.context["closing"], Decimal("529.66"))
        self.assertContains(r, "AP-RESPLIT")
        self.assertContains(r, "against Accounts Receivable (1200)")

    def test_a_date_range_carries_what_came_before(self):
        self._move(self.tatyana, "1000.00", when="2026-09-03")
        self._move(self.tatyana, "250.00", kind="invoice_sale", when="2026-09-10")
        r = self._page("1200", date_from="2026-09-05")
        self.assertEqual(r.context["opening"], Decimal("1000.00"))
        self.assertEqual(len(r.context["rows"]), 1)
        self.assertEqual(r.context["closing"], Decimal("1250.00"))

    def test_a_long_history_keeps_its_balance_true(self):
        for i in range(6):
            self._move(self.tatyana, "10.00", kind="invoice_sale", when=f"2026-09-{10 + i}")
        old = LedgerAccount.LIMIT
        LedgerAccount.LIMIT = 4
        try:
            r = self._page("1200")
        finally:
            LedgerAccount.LIMIT = old
        self.assertEqual((r.context["hidden"], len(r.context["rows"])), (2, 4))
        self.assertEqual(r.context["opening"], Decimal("20.00"))
        self.assertEqual(r.context["closing"], Decimal("60.00"))

    def test_another_books_entries_stay_out(self):
        theirs = CurrentAccount.objects.create(
            book=self.other, code="X1", name="Other", type="customer", default_currency=self.usd)
        self._move(theirs, "999.00")
        self._move(self.tatyana, "100.00")
        self.assertEqual(self._page("1200").context["closing"], Decimal("100.00"))

    def test_an_unknown_account_is_a_404(self):
        self.assertEqual(self._page("9999").status_code, 404)

    def test_the_other_pages_link_to_it(self):
        self._move(self.tatyana, "100.00")
        url = reverse("accounts:report_ledger_account", args=[self.book.pk, "1200"])
        self.assertContains(self.client.get(reverse("accounts:report_balance_sheet", args=[self.book.pk])), url)
        self.assertContains(self.client.get(reverse("accounts:report_chart_of_accounts", args=[self.book.pk])), url)
        self.assertContains(self.client.get(reverse("accounting:book_detail", args=[self.book.pk])), url)
