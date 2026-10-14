"""A book chooses the currency it charges new customers in.

Almaty keeps its books in dollars and charges its customers in tenge. The
currency a book reports in and the one its customers owe in are two
settings: a new customer account opens in the book's own choice
(CurrentAccountSettings.default_currency), else in what the book reports
in — and the order form starts there, and offers catalogue prices, which
are in dollars, converted into it.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccountSettings
from accounting.services_accounts import (
    get_or_create_current_account_for_company,
    get_or_create_current_account_for_contact, new_customer_currency,
)
from crm.models import Company, Contact


class ABookChargesInItsOwnCurrency(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        cls.kzt = CurrencyCategory.objects.create(code="KZT", name="Kazakhstani Tenge", symbol="₸")
        cls.laleli = Book.objects.create(name="Laleli Fabric", base_currency=cls.usd)
        cls.almaty = Book.objects.create(name="Almaty", base_currency=cls.usd)
        settings_row, _ = CurrentAccountSettings.objects.get_or_create(book=cls.almaty)
        settings_row.default_currency = cls.kzt
        settings_row.save()

    def test_a_book_that_chose_opens_customers_in_its_choice(self):
        self.assertEqual(new_customer_currency(self.almaty), self.kzt)

    def test_a_book_that_did_not_opens_them_in_what_it_reports_in(self):
        self.assertEqual(new_customer_currency(self.laleli), self.usd)

    def test_the_accounts_an_order_opens_follow_it(self):
        contact = Contact.objects.create(name="Dana Akhmet", directory=self.almaty.directory)
        company = Company.objects.create(name="Steppe Home", directory=self.almaty.directory)
        self.assertEqual(get_or_create_current_account_for_contact(
            contact, book=self.almaty).default_currency, self.kzt)
        self.assertEqual(get_or_create_current_account_for_company(
            company, book=self.almaty).default_currency, self.kzt)

    def test_the_books_reporting_currency_is_untouched(self):
        self.assertEqual(self.almaty.effective_base_currency, self.usd)


class TheOrderFormStartsThere(ABookChargesInItsOwnCurrency):
    def setUp(self):
        user = get_user_model().objects.create_superuser("seller_k", "s@k.com", "pw")
        user.member.books.set([self.almaty])
        user.member.default_book = self.almaty
        user.member.save()
        self.client.force_login(user)

    def test_a_new_customer_starts_in_tenge_and_the_rates_ride_with_the_page(self):
        page = self.client.get(reverse("operating:create_order_page",
                                       kwargs={"book_id": self.almaty.pk}))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertRegex(html, r'<option value="KZT"[^>]*selected')
        self.assertNotRegex(html, r'<option value="USD"[^>]*selected')
        rates = json.loads(page.context["currency_rates_json"])
        self.assertEqual(rates["USD"], 1.0)
        # The test runner's fixed table: one tenge is $0.002, so 500 ₸ = $1.
        self.assertAlmostEqual(rates["KZT"], 500.0)

    def test_a_customer_with_no_account_yet_is_priced_in_the_books_choice(self):
        contact = Contact.objects.create(name="Dana Akhmet", directory=self.almaty.directory)
        data = self.client.get(reverse("operating:customer_currency"), {
            "book": self.almaty.pk, "type": "contact", "pk": contact.pk}).json()
        self.assertEqual(data["currency"], "KZT")
        self.assertFalse(data["is_base"])
