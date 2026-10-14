"""A book has two currencies, set and explained on its page.

Reporting: what the book keeps its accounts in. Trading: what the business
sells in and is paid in. Most books have one currency for both; a branch
can keep dollar books and charge in tenge.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.forms import BookForm, CashAccountForm
from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CurrentAccountSettings
from accounting.services_accounts import new_customer_currency


class TwoCurrencies(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        cls.kzt = CurrencyCategory.objects.create(code="KZT", name="Kazakhstani Tenge", symbol="₸")
        cls.book = Book.objects.create(name="Almaty", base_currency=cls.usd)
        cls.owner = get_user_model().objects.create_superuser("owner_bc", "o@b.c", "pw")
        cls.owner.member.books.set([cls.book])
        cls.clerk = get_user_model().objects.create_user("clerk_bc", password="pw")
        cls.clerk.member.books.set([cls.book])

    def page(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("accounting:book_detail", kwargs={"pk": self.book.pk}))

    def save(self, user, **data):
        self.client.force_login(user)
        return self.client.post(
            reverse("accounting:set_book_currencies", kwargs={"pk": self.book.pk}), data)

    def test_a_book_trades_in_what_it_reports_in_until_told_otherwise(self):
        self.assertEqual(self.book.effective_trading_currency, self.usd)
        self.assertEqual(new_customer_currency(self.book), self.usd)

    def test_the_page_explains_both(self):
        body = self.page(self.owner).content.decode()
        self.assertIn("Reporting currency", body)
        self.assertIn("What this book keeps its accounts in", body)
        self.assertIn("Trading currency", body)
        self.assertIn("What this business sells in and gets paid in", body)

    def test_setting_the_trading_currency_moves_what_is_charged_not_the_books(self):
        self.save(self.owner, reporting_currency=self.usd.pk, trading_currency=self.kzt.pk)
        book = Book.objects.get(pk=self.book.pk)
        self.assertEqual(book.effective_trading_currency, self.kzt)
        self.assertEqual(book.effective_base_currency, self.usd)
        self.assertEqual(new_customer_currency(book), self.kzt)
        body = self.page(self.owner).content.decode()
        self.assertIn("Almaty sells in Kazakhstani Tenge and keeps its books in US Dollar", body)
        # Set back to the reporting currency, it follows that one again.
        self.save(self.owner, reporting_currency=self.usd.pk, trading_currency=self.usd.pk)
        self.assertIsNone(CurrentAccountSettings.objects.get(book=self.book).default_currency)

    def test_a_new_cash_account_starts_in_the_trading_currency(self):
        self.save(self.owner, reporting_currency=self.usd.pk, trading_currency=self.kzt.pk)
        form = CashAccountForm(book=Book.objects.get(pk=self.book.pk))
        self.assertEqual(form.fields["currency"].initial, self.kzt)

    def test_the_reporting_currency_is_fixed_once_there_are_entries(self):
        from accounting.models_ledger import JournalEntry
        from accounting.services_ledger import credit, debit, ensure_chart, post_entry
        ensure_chart()
        post_entry(book=self.book, date="2026-10-14", description="x",
                   lines=[debit("1000", Decimal("1")), credit("3000", Decimal("1"))])
        self.assertTrue(JournalEntry.objects.filter(book=self.book).exists())
        self.save(self.owner, reporting_currency=self.kzt.pk, trading_currency=self.kzt.pk)
        book = Book.objects.get(pk=self.book.pk)
        self.assertEqual(book.effective_base_currency, self.usd)
        self.assertEqual(book.effective_trading_currency, self.kzt)
        self.assertIn("Fixed: this book already has entries", self.page(self.owner).content.decode())

    def test_only_who_manages_the_book_may_change_them(self):
        self.save(self.clerk, reporting_currency=self.usd.pk, trading_currency=self.kzt.pk)
        self.assertEqual(Book.objects.get(pk=self.book.pk).effective_trading_currency, self.usd)
        # ...but anyone who may open the book can read them.
        body = self.page(self.clerk).content.decode()
        self.assertIn("Trading currency", body)
        self.assertNotIn("Save currencies", body)

    def test_a_new_book_can_be_given_one_when_it_is_made(self):
        form = BookForm(data={"name": "Bishkek", "total_shares": 10000000,
                              "base_currency": self.usd.pk, "trading_currency": self.kzt.pk})
        self.assertTrue(form.is_valid(), form.errors)
        book = form.save()
        self.assertEqual(book.effective_trading_currency, self.kzt)
        self.assertIn("trading_currency", BookForm().fields)
