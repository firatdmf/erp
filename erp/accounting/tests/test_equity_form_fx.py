# to run this test, use the command:
# python manage.py test accounting.test_equity_form_fx

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityCapital,
    EquityDivident,
    EquityExpense,
    ExpenseCategory,
    StakeholderBook,
)


class EquityFormFxTests(TestCase):
    """Expense, capital and dividend can each carry an entered rate."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="equity_fx", password="pw"
        )
        self.client.force_login(self.user)
        self.member = self.user.member
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        StakeholderBook.objects.create(book=self.book, member=self.member, shares=1)
        self.lira = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.try_,
            balance=Decimal("10000.00"),
        )
        self.dollars = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd,
            balance=Decimal("1000.00"),
        )

    def _entry_for(self, model, obj):
        return CashTransactionEntry.objects.get(
            content_type=ContentType.objects.get_for_model(model), content_pk=obj.pk
        )

    # -- the form renders the converter ------------------------------------
    def test_each_form_offers_a_rate_field_and_knows_the_books_currency(self):
        for name in ("add_equity_expense", "add_equity_capital", "add_equity_divident"):
            with self.subTest(form=name):
                response = self.client.get(
                    reverse(f"accounting:{name}", kwargs={"pk": self.book.pk})
                )
                self.assertContains(response, "id_exchange_rate")
                self.assertContains(response, '"code": "USD"')

    def test_cash_account_options_carry_their_currency(self):
        """The browser has to make the same currency call the server does."""
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )
        self.assertContains(response, 'data-currency-code="TRY"')
        self.assertContains(response, 'data-currency-code="USD"')

    # -- what gets saved ---------------------------------------------------
    def test_an_expense_uses_the_rate_that_was_typed(self):
        category = ExpenseCategory.objects.create(name="Contract Labor")
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self.client.post(
                reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
                {
                    "book": self.book.pk, "category": category.pk,
                    "cash_account": self.lira.pk, "currency": self.try_.pk,
                    "amount": "800.00", "date": "2026-08-20",
                    "exchange_rate": "0.030000", "description": "hamal",
                },
            )

        expense = EquityExpense.objects.get()
        self.assertEqual(expense.exchange_rate, Decimal("0.030000"))
        entry = self._entry_for(EquityExpense, expense)
        self.assertEqual(entry.exchange_rate, Decimal("0.030000"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("24.00"))

    def test_a_blank_rate_leaves_the_published_one_to_apply(self):
        category = ExpenseCategory.objects.create(name="Wages")
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self.client.post(
                reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
                {
                    "book": self.book.pk, "category": category.pk,
                    "cash_account": self.lira.pk, "currency": self.try_.pk,
                    "amount": "800.00", "date": "2026-08-20",
                    "exchange_rate": "", "description": "",
                },
            )

        expense = EquityExpense.objects.get()
        self.assertIsNone(expense.exchange_rate)
        self.assertEqual(
            self._entry_for(EquityExpense, expense).amount_in_base_currency,
            Decimal("20.00"),
        )

    def test_capital_uses_the_rate_that_was_typed(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self.client.post(
                reverse("accounting:add_equity_capital", kwargs={"pk": self.book.pk}),
                {
                    "book": self.book.pk, "member": self.member.pk,
                    "cash_account": self.lira.pk, "currency": self.try_.pk,
                    "amount": "1000.00", "date_invested": "2026-08-19",
                    "exchange_rate": "0.040000", "note": "",
                },
            )

        capital = EquityCapital.objects.get()
        self.assertEqual(capital.exchange_rate, Decimal("0.040000"))
        self.assertEqual(
            self._entry_for(EquityCapital, capital).amount_in_base_currency,
            Decimal("40.00"),
        )

    def test_a_dividend_uses_the_rate_that_was_typed(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self.client.post(
                reverse("accounting:add_equity_divident", kwargs={"pk": self.book.pk}),
                {
                    "book": self.book.pk, "member": self.member.pk,
                    "cash_account": self.lira.pk, "currency": self.try_.pk,
                    "amount": "500.00", "date": "2026-08-21",
                    "exchange_rate": "0.020000", "description": "",
                },
            )

        dividend = EquityDivident.objects.get()
        self.assertEqual(dividend.exchange_rate, Decimal("0.020000"))
        self.assertEqual(
            self._entry_for(EquityDivident, dividend).amount_in_base_currency,
            Decimal("10.00"),
        )

    def test_an_entry_in_the_books_own_currency_records_no_rate(self):
        category = ExpenseCategory.objects.create(name="Rent")
        with mock.patch("accounting.services.get_exchange_rate") as published:
            self.client.post(
                reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
                {
                    "book": self.book.pk, "category": category.pk,
                    "cash_account": self.dollars.pk, "currency": self.usd.pk,
                    "amount": "300.00", "date": "2026-08-20",
                    "exchange_rate": "", "description": "",
                },
            )
        published.assert_not_called()

        expense = EquityExpense.objects.get()
        entry = self._entry_for(EquityExpense, expense)
        self.assertIsNone(entry.exchange_rate)
        self.assertEqual(entry.amount_in_base_currency, Decimal("300.00"))
