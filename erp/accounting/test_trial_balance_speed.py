"""The mizan answers in a fixed number of queries, whatever the book holds.

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
