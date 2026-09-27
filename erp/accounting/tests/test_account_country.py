"""A new current account takes its billing country from the CRM record —
the contact's own, else their company's — and stays blank otherwise.
Never "TR" by default: a customer in Athens is not in Turkey."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.services_accounts import (
    get_or_create_current_account_for_company,
    get_or_create_current_account_for_contact,
    get_or_create_current_account_for_supplier,
)
from crm.models import Company, Contact, Supplier


class TheAccountsCountryIsTheCustomers(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        user = get_user_model().objects.create_user("staff_country", password="pw")
        self.member = user.member
        self.member.books.add(self.book)
        self.member.default_book = self.book
        self.member.save()

    def test_a_company_in_greece(self):
        company = Company.objects.create(name="Kole Greece", country="Greece")
        account = get_or_create_current_account_for_company(company, member=self.member)
        self.assertEqual(account.billing_country, "Greece")

    def test_a_contact_without_a_country_takes_their_companys(self):
        company = Company.objects.create(name="Kole Greece", country="Greece")
        contact = Contact.objects.create(name="Nick", company=company)
        account = get_or_create_current_account_for_contact(contact, member=self.member)
        self.assertEqual(account.billing_country, "Greece")

    def test_a_contacts_own_country_wins(self):
        company = Company.objects.create(name="Kole Greece", country="Greece")
        contact = Contact.objects.create(name="Nick", company=company, country="Cyprus")
        account = get_or_create_current_account_for_contact(contact, member=self.member)
        self.assertEqual(account.billing_country, "Cyprus")

    def test_no_country_anywhere_stays_blank(self):
        contact = Contact.objects.create(name="Nobody Knows")
        account = get_or_create_current_account_for_contact(contact, member=self.member)
        self.assertEqual(account.billing_country, "")

    def test_a_supplier_too(self):
        supplier = Supplier.objects.create(company_name="Bursa Mill", country="Türkiye")
        account = get_or_create_current_account_for_supplier(supplier, member=self.member)
        self.assertEqual(account.billing_country, "Türkiye")
