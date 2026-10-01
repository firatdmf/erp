"""A customer typed into the order form's "create new" panel is made with
the order — not before it, so a form closed halfway leaves no CRM record."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from decimal import Decimal

from accounting.models import Book, CurrencyCategory, CurrentAccountMovement
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact
from marketing.models import Product
from operating.models import Order


class TheNewCustomerIsSavedWithTheOrder(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        Product.objects.create(title="Krep", sku="KRP", featured=False)
        user = get_user_model().objects.create_superuser("seller_new", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _post(self, **extra):
        line = {"item_no": 1, "product": {"sku": "KRP", "variant": False},
                "description": "", "quantity": 10, "outsourced": 0,
                "price": 2, "is_custom_curtain": False, "rolls": []}
        data = {"customer_type": "contact", "customer_pk": "", "book": self.book.pk,
                "product_json_input": json.dumps([line])}
        data.update(extra)
        return self.client.post(reverse("operating:create_order"), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_a_contact_is_made_with_the_order_and_gets_its_account(self):
        resp = self._post(new_customer_json=json.dumps(
            {"name": "trial 222", "phone": "+90 555", "email": "t@t.com", "address": "Fatih"}))
        self.assertIn(resp.status_code, (200, 302), resp.content)
        contact = Contact.objects.get(name="trial 222")
        self.assertEqual(contact.phone, ["+90 555"])
        self.assertEqual(contact.email, ["t@t.com"])
        order = Order.objects.get()
        self.assertEqual(order.contact, contact)
        self.assertEqual(CurrentAccount.objects.get(contact=contact).book, self.book)

    def test_a_company_too(self):
        resp = self._post(customer_type="company",
                          new_customer_json=json.dumps({"name": "Trial Ltd"}))
        self.assertIn(resp.status_code, (200, 302), resp.content)
        self.assertEqual(Order.objects.get().company, Company.objects.get(name="Trial Ltd"))

    def test_without_a_customer_nothing_is_made(self):
        resp = self._post()
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_a_blank_name_is_no_customer(self):
        resp = self._post(new_customer_json=json.dumps({"name": "  "}))
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(Contact.objects.count(), 0)

    def test_a_company_that_exists_is_not_made_twice(self):
        Company.objects.create(name="Trial Ltd")
        resp = self._post(customer_type="company",
                          new_customer_json=json.dumps({"name": "trial ltd"}))
        self.assertFalse(resp.json()["ok"])
        self.assertIn("already exists", resp.json()["error"])
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 0)

    def test_a_new_contact_brings_their_company_with_them(self):
        resp = self._post(new_customer_json=json.dumps(
            {"name": "Ayşe", "company": "Trial Tekstil"}))
        self.assertIn(resp.status_code, (200, 302), resp.content)
        contact = Contact.objects.get(name="Ayşe")
        self.assertEqual(contact.company, Company.objects.get(name="Trial Tekstil"))
        self.assertEqual(Order.objects.get().contact, contact)

    def test_a_company_crm_already_has_is_linked_not_made_again(self):
        existing = Company.objects.create(name="Trial Tekstil")
        resp = self._post(new_customer_json=json.dumps(
            {"name": "Ayşe", "company": "trial tekstil"}))
        self.assertIn(resp.status_code, (200, 302), resp.content)
        self.assertEqual(Contact.objects.get(name="Ayşe").company, existing)
        self.assertEqual(Company.objects.count(), 1)

    def test_no_company_leaves_an_individual(self):
        self._post(new_customer_json=json.dumps({"name": "Ayşe", "company": "  "}))
        self.assertIsNone(Contact.objects.get(name="Ayşe").company)
        self.assertEqual(Company.objects.count(), 0)

    # The panel's currency opens the new account in it, and the order is
    # priced in it — there is no account yet to say otherwise.

    def test_the_account_and_the_order_take_the_currency(self):
        resp = self._post(new_customer_json=json.dumps({"name": "Nikos", "currency": "eur"}))
        self.assertIn(resp.status_code, (200, 302), resp.content)
        contact = Contact.objects.get(name="Nikos")
        self.assertEqual(CurrentAccount.objects.get(contact=contact).default_currency, self.eur)
        self.assertEqual(Order.objects.get().currency, self.eur)

    def test_no_currency_leaves_the_default(self):
        self._post(new_customer_json=json.dumps({"name": "Nikos"}))
        account = CurrentAccount.objects.get(contact__name="Nikos")
        self.assertEqual(account.default_currency, self.usd)

    def test_an_unused_account_of_the_company_is_moved_over(self):
        company = Company.objects.create(name="Athens Home")
        CurrentAccount.objects.create(book=self.book, company=company, name="Athens Home",
                                      type="customer", default_currency=self.usd)
        self._post(new_customer_json=json.dumps(
            {"name": "Nikos", "company": "Athens Home", "currency": "EUR"}))
        self.assertEqual(CurrentAccount.objects.get(company=company).default_currency, self.eur)
        self.assertEqual(Order.objects.get().currency, self.eur)

    def test_a_used_account_in_another_currency_refuses_the_order(self):
        company = Company.objects.create(name="Athens Home")
        account = CurrentAccount.objects.create(
            book=self.book, company=company, name="Athens Home",
            type="customer", default_currency=self.usd)
        CurrentAccountMovement.objects.create(
            current_account=account, book=self.book, date="2026-09-11",
            amount=Decimal("100.00"), currency=self.usd, movement_type="adjustment",
            exchange_rate=Decimal("1"), amount_base=Decimal("100.00"))
        resp = self._post(new_customer_json=json.dumps(
            {"name": "Nikos", "company": "Athens Home", "currency": "EUR"}))
        self.assertFalse(resp.json()["ok"])
        self.assertIn("USD", resp.json()["error"])
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_the_panel_offers_every_currency(self):
        resp = self.client.get(reverse("operating:create_order_page", args=[self.book.pk]))
        self.assertContains(resp, 'id="co-nc-currency"')
        self.assertContains(resp, '<option value="EUR"')

    def test_the_company_field_searches_companies_only(self):
        Company.objects.create(name="Trial Tekstil")
        Contact.objects.create(name="Trial Person")
        url = reverse("crm:customer_autocomplete")
        html = self.client.get(url, {"customer": "trial", "only": "company"}).content.decode()
        self.assertIn("Trial Tekstil", html)
        self.assertNotIn("Trial Person", html)
        # No match is no list at all: the typed name is the new company.
        self.assertEqual(self.client.get(url, {"customer": "zzz", "only": "company"}).content, b"")
