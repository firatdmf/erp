"""The mizan answers fast, and in one currency.

Run with:
    python manage.py test accounting.test_trial_balance_speed
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement


class TrialBalanceQueryCount(TestCase):
    """It used to run three aggregates per account inside a Python loop.
    Laleli has 1,277 active accounts, so the page asked a database at the
    far end of a proxy connection 3,831 questions and took minutes.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Laleli Fabric", base_currency=self.usd)
        user = get_user_model().objects.create_user("acct", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

    def _accounts(self, n, start=0):
        for i in range(start, start + n):
            cari = CariAccount.objects.create(
                book=self.book, code=f"{i:05d}", name=f"ACCOUNT {i}",
                default_currency=self.usd)
            CariMovement.objects.create(
                cari=cari, book=self.book, date="2026-02-01",
                amount=Decimal("100.00"), currency=self.usd,
                movement_type="opening", description="ob")
            CariMovement.objects.create(
                cari=cari, book=self.book, date="2026-03-01",
                amount=Decimal("-40.00"), currency=self.usd,
                movement_type="collection", description="col")
            cari.recompute_balance(save=True)

    def _page(self, **params):
        return self.client.get(
            reverse("accounts:report_trial_balance", args=[self.book.pk]),
            {"date_from": "2026-01-01", "date_to": "2026-12-31", **params})

    def test_the_page_still_answers(self):
        self._accounts(3)
        resp = self._page()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ACCOUNT 1")

    def test_it_reports_opening_debits_and_credits_per_account(self):
        self._accounts(1)
        rows = self._page().context["rows"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Both movements fall inside the period, so nothing is opening.
        self.assertEqual(row["opening"], Decimal("0.00"))
        self.assertEqual(row["debits"], Decimal("100.00"))
        self.assertEqual(row["credits"], Decimal("40.00"))
        self.assertEqual(row["closing"], Decimal("60.00"))

    def test_movements_before_the_period_land_in_opening(self):
        self._accounts(1)
        resp = self._page(date_from="2026-02-15")
        row = resp.context["rows"][0]
        self.assertEqual(row["opening"], Decimal("100.00"))
        self.assertEqual(row["credits"], Decimal("40.00"))
        self.assertEqual(row["closing"], Decimal("60.00"))

    def test_the_query_count_does_not_grow_with_the_book(self):
        """The whole point. Five accounts and fifty must cost the same."""
        self._accounts(5)
        small = self._measure()
        # Ten times the accounts, added rather than swapped in: a
        # collection movement mints a Payment, and Payment.cari is
        # PROTECTed, so these rows cannot be deleted and recreated.
        self._accounts(45, start=5)
        large = self._measure()
        self.assertEqual(small, large,
                         f"{small} queries for 5 accounts, {large} for 50 — "
                         f"the page is querying per account again")

    def _measure(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self._page()
        return len(ctx)


class EveryFigureIsBaseCurrency(TestCase):
    """It summed `amount` — the ENTERED figure, in whatever currency the
    movement was written in. Laleli holds 877 dollar movements, 16 lira and
    2 euro, and six accounts carry more than one, so the page added lira to
    dollars as though they were the same unit. The grand total read
    302,676.10 against a real position of 349,327.22.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="\u20ba")
        self.book = Book.objects.create(
            name="Laleli Fabric", base_currency=self.usd)
        user = get_user_model().objects.create_user("mizan", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

        self.cari = CariAccount.objects.create(
            book=self.book, code="00001", name="MIXED",
            default_currency=self.usd)

    def _mv(self, amount, currency, rate=None):
        return CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-03-01",
            amount=Decimal(amount), currency=currency, exchange_rate=rate,
            movement_type="opening", description="ob")

    def _row(self):
        resp = self.client.get(
            reverse("accounts:report_trial_balance", args=[self.book.pk]),
            {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        self.assertEqual(resp.status_code, 200)
        return resp.context["rows"][0]

    def test_a_lira_movement_counts_as_what_it_is_worth(self):
        self._mv("100.00", self.usd)
        lira = self._mv("300.00", self.try_, Decimal("0.02083300"))
        # Whatever rate the movement resolves for itself, 300 lira is worth
        # a few dollars and nothing like 300 of them. The assertion reads
        # amount_base rather than restating the FX arithmetic, which is
        # CariMovement's job and tested where that lives.
        lira.refresh_from_db()
        self.assertLess(lira.amount_base, Decimal("50.00"))
        self.assertEqual(self._row()["debits"],
                         Decimal("100.00") + lira.amount_base)

    def test_the_page_no_longer_adds_lira_to_dollars(self):
        self._mv("100.00", self.usd)
        self._mv("300.00", self.try_, Decimal("0.02083300"))
        # The old sum over `amount` would have said 400.00.
        self.assertNotEqual(self._row()["debits"], Decimal("400.00"))

    def test_the_closing_total_agrees_with_the_account_balance(self):
        """cached_balance is already base currency, so the mizan and the
        account page used to contradict each other."""
        self._mv("100.00", self.usd)
        self._mv("300.00", self.try_, Decimal("0.02083300"))
        self.cari.recompute_balance(save=True)
        self.cari.refresh_from_db()
        self.assertEqual(self._row()["closing"], self.cari.cached_balance)

    def test_the_header_says_which_currency(self):
        self._mv("100.00", self.usd)
        resp = self.client.get(
            reverse("accounts:report_trial_balance", args=[self.book.pk]),
            {"date_from": "2026-01-01", "date_to": "2026-12-31"})
        self.assertContains(resp, "USD")
