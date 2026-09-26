"""A customer typed into the order form's "create new" panel is made with
the order — not before it, so a form closed halfway leaves no CRM record."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact
from marketing.models import Product
from operating.models import Order


class TheNewCustomerIsSavedWithTheOrder(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
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
