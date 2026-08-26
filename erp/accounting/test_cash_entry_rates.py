# to run this test, use the command:
# python manage.py test accounting.test_cash_entry_rates

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityExpense,
)
from accounting.models_accounts import CariAccount, Payment


class CashEntryRateTests(TestCase):
    """Which rate converts an entry, and whether it can move afterwards."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.lira = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.try_, balance=Decimal("0.00")
        )
        self.dollars = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("0.00")
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Rana", type="customer",
            default_currency=self.try_,
        )

    def _expense_entry(self, currency, account, amount="200.00", on="2026-08-17"):
        expense = EquityExpense.objects.create(
            book=self.book, cash_account=account, currency=currency,
            amount=Decimal(amount), date=on, description="",
        )
        return CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityExpense),
            content_pk=expense.pk,
            amount=Decimal(amount),
            is_amount_positive=False,
            currency=currency,
            cash_account=account,
        )

    # -- base currency -----------------------------------------------------
    def test_an_entry_in_the_books_own_currency_records_no_rate(self):
        """Nothing was converted, so there is no rate to state."""
        entry = self._expense_entry(self.usd, self.dollars)
        self.assertIsNone(entry.exchange_rate)
        self.assertEqual(entry.amount_in_base_currency, Decimal("200.00"))

    # -- date-aware --------------------------------------------------------
    def test_conversion_uses_the_rate_for_the_day_the_money_moved(self):
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")
            entry = self._expense_entry(self.try_, self.lira, on="2026-08-17")

        self.assertEqual(rate.call_args.kwargs["on_date"], date(2026, 8, 17))
        self.assertEqual(entry.exchange_rate, Decimal("0.025"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("5.00"))

    # -- entered rate wins -------------------------------------------------
    def test_a_rate_entered_on_the_payment_beats_the_published_one(self):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-1", type="collection",
            method="cash", status="draft", date=date(2026, 8, 17),
            amount=Decimal("200.00"), currency=self.try_,
            cash_account=self.lira,
            exchange_rate=Decimal("0.030000"),   # what the teller actually got
        )
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")  # what the API says
            payment.confirm()

        entry = CashTransactionEntry.objects.get(
            content_type=ContentType.objects.get_for_model(Payment),
            content_pk=payment.pk,
        )
        self.assertEqual(entry.exchange_rate, Decimal("0.030000"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("6.00"))

    def test_the_entered_rate_survives_a_later_save(self):
        """'Permanently' — re-saving must not quietly reconvert."""
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")
            entry = self._expense_entry(self.try_, self.lira)

        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.099")  # the market moved
            entry.save()
            entry.refresh_from_db()

        self.assertEqual(entry.exchange_rate, Decimal("0.025000"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("5.00"))
        rate.assert_not_called()

    def test_a_rate_already_on_the_entry_is_never_overridden(self):
        expense = EquityExpense.objects.create(
            book=self.book, cash_account=self.lira, currency=self.try_,
            amount=Decimal("200.00"), date="2026-08-17", description="",
        )
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            entry = CashTransactionEntry.objects.create(
                book=self.book,
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
                amount=Decimal("200.00"),
                is_amount_positive=False,
                currency=self.try_,
                cash_account=self.lira,
                exchange_rate=Decimal("0.040000"),
            )
        rate.assert_not_called()
        self.assertEqual(entry.amount_in_base_currency, Decimal("8.00"))


class BookBaseCurrencyTests(TestCase):
    def test_a_book_reports_in_its_own_currency(self):
        try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        book = Book.objects.create(name="Lira Book", base_currency=try_)
        self.assertEqual(book.effective_base_currency, try_)

    def test_a_book_without_one_falls_back_to_the_deployment_default(self):
        CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )
        book = Book.objects.create(name="Unset Book")
        self.assertEqual(book.effective_base_currency.code, "USD")


class RateDateCoercionTests(TestCase):
    """A date can reach the rate lookup as text, and must still work.

    A model field assigned "2026-08-17" holds the string until the row is
    reloaded, so an unsaved entry hands over text. Comparing that to
    date.today() raises TypeError, which the fetcher caught as "no source
    had it" — the conversion then failed for a reason unrelated to FX.
    """

    def test_a_string_date_is_understood(self):
        from accounting.services import _as_date

        self.assertEqual(_as_date("2026-08-17"), date(2026, 8, 17))

    def test_a_real_date_passes_through(self):
        from accounting.services import _as_date

        self.assertEqual(_as_date(date(2026, 8, 17)), date(2026, 8, 17))

    def test_none_stays_none(self):
        from accounting.services import _as_date

        self.assertIsNone(_as_date(None))

    def test_an_entry_dated_with_a_string_converts_at_that_date(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        book = Book.objects.create(name="Book", base_currency=usd)
        account = CashAccount.objects.create(
            book=book, name="Cash", currency=try_, balance=Decimal("0.00")
        )
        expense = EquityExpense.objects.create(
            book=book, cash_account=account, currency=try_,
            amount=Decimal("200.00"), date="2026-08-17", description="",
        )
        with mock.patch("accounting.services._fetch_rate") as fetch:
            fetch.return_value = Decimal("0.025")
            entry = CashTransactionEntry.objects.create(
                book=book,
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
                amount=Decimal("200.00"),
                is_amount_positive=False,
                currency=try_,
                cash_account=account,
            )

        self.assertEqual(fetch.call_args.kwargs["on_date"], date(2026, 8, 17))
        self.assertEqual(entry.amount_in_base_currency, Decimal("5.00"))
