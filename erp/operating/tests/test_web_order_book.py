# to run this test, use the command:
# python manage.py test operating.tests.test_web_order_book

"""A web order is a signed-in customer's, charged to their contact's
account in the book web orders land in — so it is that book's order.

It used to arrive with no customer and no current account, which put it
in no book: no order list showed it. See operating/web_orders.py.
"""
import json

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.client_tokens import issue
from authentication.models import WebClient
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import Order

URL = "/operating/orders/create/"


class WebOrderBookTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        Book.objects.create(name="Older book")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.settings = override_settings(CURRENT_ACCOUNT_BOOK_ID=str(self.laleli.pk))
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.product = Product.objects.create(title="Krep", sku="KRP", featured=False)
        ProductVariant.objects.create(product=self.product, variant_sku="KRP.WHITE")
        self.ayse = WebClient.objects.create(
            username="ayse", email="Ayse@Example.com", name="Ayşe Yılmaz", phone="+905551112233",
            password=make_password("pw"), is_active=True)
        self.client = Client()

    def post(self, web_client=None, token=None, **extra):
        items = extra.pop("items", [{"product_sku": "KRP", "product_variant_sku": "KRP.WHITE",
                                     "quantity": 3, "price": "4.50"}])
        body = {"items": items, "original_currency": "USD", **extra}
        headers = {}
        if token or web_client:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token or issue(web_client)}"
        return self.client.post(URL, json.dumps(body), content_type="application/json", **headers)

    def test_no_sign_in_no_order(self):
        for token in (None, "forged"):
            with self.subTest(token=token):
                r = self.post(token=token, web_client_id=self.ayse.pk)
                self.assertEqual(r.status_code, 401)
        self.assertFalse(Order.objects.exists())

    def test_the_body_cannot_name_another_customer(self):
        can = WebClient.objects.create(username="can", email="can@example.com", name="Can",
                                       password=make_password("pw"), is_active=True)
        self.assertEqual(self.post(can, web_client_id=self.ayse.pk, is_guest_order=True).status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.web_client, can)
        self.assertFalse(order.is_guest_order)

    def test_the_order_is_the_web_orders_books_with_a_contact_made_from_the_customer(self):
        self.assertEqual(self.post(self.ayse).status_code, 201)
        order = Order.objects.get()
        contact = order.contact
        self.assertEqual(contact.name, "Ayşe Yılmaz")
        self.assertEqual(contact.email, ["Ayse@Example.com"])
        self.assertEqual(contact.phone, ["+905551112233"])
        self.assertEqual(contact.directory_id, self.laleli.directory_id)
        self.assertEqual(order.current_account.book, self.laleli)
        self.assertEqual(order.current_account.contact, contact)
        self.assertEqual(order.currency, self.usd)
        self.ayse.refresh_from_db()
        self.assertEqual(self.ayse.contact, contact)

    def test_the_second_order_reuses_the_contact_and_account(self):
        self.post(self.ayse)
        self.post(self.ayse)
        first, second = Order.objects.order_by("pk")
        self.assertEqual(first.contact, second.contact)
        self.assertEqual(first.current_account, second.current_account)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(CurrentAccount.objects.filter(contact=first.contact).count(), 1)

    def test_a_contact_with_her_email_is_hers_whatever_its_case(self):
        known = Contact.objects.create(name="Ayşe Y. (phone)", email=["ayse@example.com"],
                                       directory=self.laleli.directory)
        self.post(self.ayse)
        self.assertEqual(Order.objects.get().contact, known)

    def test_a_stranger_with_her_name_is_not_charged(self):
        stranger = Contact.objects.create(name="Ayşe Yılmaz", email=["other@example.com"],
                                          directory=self.laleli.directory)
        self.post(self.ayse)
        contact = Order.objects.get().contact
        self.assertNotEqual(contact, stranger)
        self.assertEqual(contact.name, f"Ayşe Yılmaz (web #{self.ayse.pk})")

    def test_a_customer_who_gave_only_a_business_name_gets_a_contact_by_it(self):
        self.ayse.name = None
        self.ayse.web_client_settings = {"company_name": "Ayşe Tekstil"}
        self.ayse.save()
        self.post(self.ayse)
        self.assertEqual(Order.objects.get().contact.name, "Ayşe Tekstil")

    def test_it_shows_in_the_books_order_list(self):
        self.post(self.ayse)
        order = Order.objects.get()
        self.assertTrue(Order.objects.filter(current_account__book=self.laleli, pk=order.pk).exists())

    # ── Every line names a variant the catalog has ──────────────────
    def test_the_line_is_the_variant_chosen(self):
        self.assertEqual(self.post(self.ayse).status_code, 201)
        self.assertEqual(Order.objects.get().items.get().product_variant.variant_sku, "KRP.WHITE")

    def test_the_variant_is_found_whatever_its_case(self):
        r = self.post(self.ayse, items=[{"product_sku": "krp", "product_variant_sku": "krp.white",
                                         "quantity": 3, "price": "4.50"}])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Order.objects.get().items.get().product_variant.variant_sku, "KRP.WHITE")

    def test_a_line_without_a_variant_refuses_the_order(self):
        good = {"product_sku": "KRP", "product_variant_sku": "KRP.WHITE", "quantity": 1, "price": "4.50"}
        bare = {"product_sku": "KRP", "quantity": 3, "price": "4.50"}
        r = self.post(self.ayse, items=[good, bare])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["unknown"], ["KRP"])
        self.assertFalse(Order.objects.exists())

    def test_a_variant_the_catalog_does_not_have_refuses_the_order(self):
        for line in ({"product_sku": "KRP", "product_variant_sku": "KRP.WHITE-SAMPLE"},
                     {"product_sku": "GONE", "product_variant_sku": "GONE.RED"},
                     {"product_sku": "OTHER", "product_variant_sku": "KRP.WHITE"}):
            with self.subTest(line=line):
                r = self.post(self.ayse, items=[{**line, "quantity": 1, "price": "4.50"}])
                self.assertEqual(r.status_code, 409)
                self.assertEqual(r.json()["unknown"], [line["product_variant_sku"]])
        self.assertFalse(Order.objects.exists())
