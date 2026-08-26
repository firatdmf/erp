# to run this test, use the command:
# python manage.py test accounting.test_cash_running_balance

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityCapital,
)
from django.contrib.auth import get_user_model


class CashEntryTestBase(TestCase):
    """Shared fixture: one book, one USD kasa, and a way to move money.

    Everything here stays in the base currency (USD) so no FX rate is
    fetched — the drift being tested has nothing to do with conversion.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )[0]
        self.book = Book.objects.create(name="Laleli Fabric")
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("0.00")
        )
        # A Member is created for every user by signal — take that one.
        user = get_user_model().objects.create_user(username="teller", password="pw")
        self.member = user.member

    def _entry(self, amount, positive):
        """Move the cash account, then record the entry — the caller's order.

        Moved with an F() UPDATE rather than instance.save() so the helper
        neither clobbers a balance changed behind its back nor trips
        CashAccount.clean()'s no-negative rule, which the real cash-moving
        paths (Payment.post) also bypass.
        """
        delta = Decimal(amount) if positive else -Decimal(amount)
        CashAccount.objects.filter(pk=self.kasa.pk).update(
            balance=models.F("balance") + delta
        )
        self.kasa.refresh_from_db()
        # content_* just needs to point at something real; the running total
        # is not derived from it.
        capital = EquityCapital.objects.create(
            book=self.book,
            member=self.member,
            date_invested="2026-08-19",
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal(amount),
        )
        return CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=capital.pk,
            amount=Decimal(amount),
            is_amount_positive=positive,
            currency=self.usd,
            cash_account=self.kasa,
        )


class CashRunningBalanceTests(CashEntryTestBase):
    """total_base_currency_balance must track the real cash."""

    def test_running_total_follows_the_entries(self):
        self.assertEqual(self._entry("600.00", True).total_base_currency_balance,
                         Decimal("600.00"))
        self.assertEqual(self._entry("100.00", False).total_base_currency_balance,
                         Decimal("500.00"))

    def test_cash_moved_without_an_entry_is_still_counted(self):
        """The drift that put book 2 at $59.60 against a real $1,804.98.

        Payment.post() updates CashAccount.balance with a raw F() UPDATE and
        writes no entry here. The next entry must still report the book's
        true total, not the stale chain.
        """
        self._entry("600.00", True)

        # A confirmed Payment lands $1,245 in the kasa, writing no entry.
        CashAccount.objects.filter(pk=self.kasa.pk).update(
            balance=Decimal("600.00") + Decimal("1245.00")
        )

        entry = self._entry("100.00", False)
        # 600 + 1245 - 100
        self.assertEqual(entry.total_base_currency_balance, Decimal("1745.00"))

    def test_resaving_an_entry_does_not_restamp_it(self):
        """History must not be rewritten to today's total on any later save."""
        entry = self._entry("600.00", True)
        self._entry("400.00", True)

        entry.refresh_from_db()
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.total_base_currency_balance, Decimal("600.00"))

    def test_a_negative_total_is_not_flattened_to_zero(self):
        """The old code clamped anything under a cent to 0.00, sign and all."""
        self._entry("100.00", True)
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("-250.00"))

        entry = self._entry("50.00", False)
        self.assertEqual(entry.total_base_currency_balance, Decimal("-300.00"))


class CashEntryDateTests(CashEntryTestBase):
    """The entry files under the date the money moved, not the day it was typed."""

    def test_date_comes_from_the_source_not_today(self):
        entry = self._entry("600.00", True)
        # _entry's EquityCapital is dated 19 Aug 2026; the row is created now.
        self.assertEqual(str(entry.date), "2026-08-19")
        self.assertNotEqual(entry.date, entry.created_at.date())

    def test_a_backdated_exchange_keeps_its_own_date(self):
        """The case that started this: entered on the 26th, dated the 21st."""
        from accounting.models import CurrencyExchange

        other = CashAccount.objects.create(
            book=self.book, name="Kasa TRY", currency=self.usd, balance=Decimal("0.00")
        )
        exchange = CurrencyExchange.objects.create(
            book=self.book,
            from_cash_account=self.kasa,
            to_cash_account=other,
            from_amount=Decimal("200.00"),
            to_amount=Decimal("200.00"),
            date="2026-08-21",
        )
        entry = CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(CurrencyExchange),
            content_pk=exchange.pk,
            amount=Decimal("200.00"),
            is_amount_positive=False,
            currency=self.usd,
            cash_account=self.kasa,
        )
        self.assertEqual(str(entry.date), "2026-08-21")

    def test_an_explicit_date_is_not_overwritten(self):
        entry = CashTransactionEntry(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=1,
            amount=Decimal("10.00"),
            is_amount_positive=True,
            currency=self.usd,
            cash_account=self.kasa,
            date="2026-01-05",
        )
        entry.save()
        self.assertEqual(str(entry.date), "2026-01-05")


class CashEntryDateBackfillTests(CashEntryTestBase):
    """Migration 0077's backfill, exercised on real rows.

    The function takes `apps`, so it can be handed the live registry and
    called directly — cheaper than standing up a migration harness, and it
    tests the query shape that actually runs against production.
    """

    @staticmethod
    def _backfill():
        """Call migration 0077's backfill against the live app registry."""
        from importlib import import_module
        from django.apps import apps as registry

        module = import_module(
            "accounting.migrations.0077_cash_transaction_entry_date"
        )
        module.backfill_dates(registry, None)

    def _blank_the_dates(self):
        CashTransactionEntry.objects.update(date=None)

    def test_backfill_fills_every_row_from_its_source(self):
        capital_entry = self._entry("600.00", True)
        self._blank_the_dates()
        self.assertIsNone(
            CashTransactionEntry.objects.get(pk=capital_entry.pk).date
        )

        self._backfill()

        capital_entry.refresh_from_db()
        # EquityCapital keeps its date on date_invested, not date.
        self.assertEqual(str(capital_entry.date), "2026-08-19")

    def test_backfill_is_a_handful_of_queries_not_one_per_row(self):
        """The shape that made the first attempt unusable over the proxy."""
        for _ in range(8):
            self._entry("10.00", True)
        self._blank_the_dates()

        # 8 rows sharing one source model and one date: reading the rows,
        # the content types, the source dates, then a single grouped UPDATE.
        with self.assertNumQueries(4):
            self._backfill()

        self.assertFalse(
            CashTransactionEntry.objects.filter(date__isnull=True).exists()
        )
