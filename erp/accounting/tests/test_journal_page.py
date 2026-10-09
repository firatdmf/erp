"""The journal: every entry, with what it debited and what it credited.

Run with:
    python manage.py test accounting.tests.test_journal_page
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import (CurrentAccount, CurrentAccountMovement,
                                        CurrentAccountTransfer)
from accounting.services_ledger import ensure_chart


class JournalPage(TestCase):
    """The transactions page lists cash and nothing else, so a transfer
    between two accounts — or a sale nobody has paid for — was on no list
    at all."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.other = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.samir = CurrentAccount.objects.create(
            book=self.book, code="ERGTH", name="SAMIR", type="customer", default_currency=self.usd)
        self.demfirat = CurrentAccount.objects.create(
            book=self.book, code="ACC-101", name="DEMFIRAT", type="customer", default_currency=self.usd)
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

    def _page(self, book=None, **params):
        return self.client.get(
            reverse("accounts:report_journal", args=[(book or self.book).pk]), params)

    def _sides(self, row):
        return ([l.account.code for l in row["debits"]], [l.account.code for l in row["credits"]])

    def test_a_sale_on_account_names_both_sides(self):
        self._move(self.samir, "250.00", kind="invoice_sale", text="a sale")
        r = self._page()
        self.assertEqual(r.status_code, 200)
        row = r.context["rows"][0]
        self.assertEqual(self._sides(row), (["1200"], ["4000"]))
        self.assertEqual(row["amount"], Decimal("250.00"))
        self.assertContains(r, "Accounts Receivable (1200)")
        self.assertContains(r, "Sales (4000)")
        self.assertContains(r, "ERGTH")             # whose receivable it was

    def test_a_transfer_between_two_accounts_is_on_it(self):
        """The row that started this: no cash moved, so the cash journal
        never heard of it."""
        self._move(self.samir, "1000.00")
        with self.captureOnCommitCallbacks(execute=True):
            transfer = CurrentAccountTransfer.objects.create(
                book=self.book, date="2026-10-06", from_current_account=self.samir,
                to_current_account=self.demfirat, amount=Decimal("950.00"), currency=self.usd)
            transfer.post()
        rows = [row for row in self._page().context["rows"]
                if str(row["entry"].date) == "2026-10-06"]
        self.assertEqual(len(rows), 2)
        parties = {l.current_account.code for row in rows
                   for l in row["debits"] + row["credits"] if l.current_account}
        self.assertEqual(parties, {"ERGTH", "ACC-101"})

    def test_newest_first_and_only_this_book(self):
        self._move(self.samir, "100.00", when="2026-09-01", text="older")
        self._move(self.samir, "200.00", when="2026-09-20", text="newer")
        elsewhere = CurrentAccount.objects.create(
            book=self.other, code="X-1", name="ELSEWHERE", type="customer", default_currency=self.usd)
        self._move(elsewhere, "999.00", text="another book")
        r = self._page()
        self.assertEqual([row["entry"].description for row in r.context["rows"]],
                         ["newer", "older"])
        self.assertNotContains(r, "another book")

    def test_the_filters_narrow_it(self):
        self._move(self.samir, "100.00", when="2026-09-01", text="older")
        self._move(self.samir, "-150.00", when="2026-09-20", text="in credit now")
        self.assertEqual(self._page(date_to="2026-09-10").context["count"], 1)
        # Going into credit makes the ledger re-split payables: an entry
        # with no document behind it.
        ledger_only = self._page(kind="ledger").context["rows"]
        self.assertTrue(ledger_only)
        self.assertTrue(all(row["entry"].source_id is None for row in ledger_only))
        accounts = self._page(kind="accounts").context["rows"]
        self.assertEqual(len(accounts), 2)
        self.assertTrue(accounts[0]["url"])         # opens the ledger row behind it

    def test_an_entry_in_another_currency_says_what_was_entered(self):
        """The journal is in the book's currency; the lira somebody typed
        is shown under it. An entry already in dollars repeats nothing."""
        lira = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        with self.captureOnCommitCallbacks(execute=True):
            CurrentAccountMovement.objects.create(
                current_account=self.samir, book=self.book, movement_type="collection",
                date="2026-09-05", amount=Decimal("-5000.00"), currency=lira,
                exchange_rate=Decimal("0.02"), amount_base=Decimal("-100.00"), description="in lira")
        self._move(self.samir, "250.00", kind="invoice_sale", when="2026-09-04", text="in dollars")
        r = self._page()
        rows = {row["entry"].description: row for row in r.context["rows"]}
        self.assertEqual(rows["in lira"]["amount"], Decimal("100.00"))
        self.assertEqual(rows["in lira"]["originals"], [(Decimal("5000.00"), "TRY")])
        self.assertEqual(rows["in dollars"]["originals"], [])
        self.assertContains(r, "5,000.00 TRY")
