"""The order list without Prices and customers: what to pack, not the sale.

Operations see orders, pack and ship them; who an order is for and what
it is worth are the sale's (erp.roles.sees_order_money). The list shows
them where an order goes instead of who it is for, and no total — not in
a cell, a search index or a data- attribute. Staff, who hold the
permission, see the list as before.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderItem


class OrderListWithoutPricesAndCustomers(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.test/qr.png")
    def setUp(self, _upload):
        self.book = Book.objects.create(name="Ergene Fabric")
        account = CurrentAccount.objects.create(
            book=self.book, code="C-901", name="Zircon Buyer Ltd", type="customer",
            default_currency=CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$"))
        contact = Contact.objects.create(name="Zircon Buyer Ltd", email=["buyer@zircon.test"])
        self.order = Order.objects.create(
            order_number="DK0000901", current_account=account, contact=contact,
            status="packaging", delivery_city="Tashkent", delivery_country="Uzbekistan",
            delivery_address="Amir Temur 12")
        product = Product.objects.create(title="Crepe", sku="KZL000901")
        OrderItem.objects.create(
            order=self.order, product=product,
            product_variant=product.variants.create(
                variant_sku="KZL000901", variant_price=10, variant_cost=Decimal("4.00")),
            quantity=Decimal("1.00"), price=Decimal("1234.56"))

    def sign_in(self, name, *grants):
        """`grants` as a role writes them: Operations hold the packing_only
        restriction because their role lacks Prices and customers."""
        user = User.objects.create_user(name, password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        for grant in grants:
            user.member.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        self.client.force_login(user)

    def list_page(self):
        return self.client.get(reverse("operating:order_list_scoped", kwargs={"book_id": self.book.pk}))

    def assert_no_sale(self, body):
        for secret in ("Zircon Buyer", "buyer@zircon.test", "1234.56", "1,234.56", "1.234,56"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, body)

    def test_operations_see_what_to_pack_and_where_it_goes(self):
        self.sign_in("mustafa", "orders", "beyond_sales", "print_labels", "packing_only")
        resp = self.list_page()
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("DK0000901", body)
        self.assertIn("Tashkent", body)
        self.assertIn("Crepe", body)  # products stay searchable
        self.assert_no_sale(body)
        self.assertNotIn(reverse("operating:create_order_page", args=[self.book.pk]), body)

    def test_a_profit_grant_without_prices_still_shows_no_profit(self):
        self.sign_in("mustafa", "orders", "beyond_sales", "view_profit", "packing_only")
        body = self.list_page().content.decode()
        self.assertNotIn('<div class="num ord-gross-cell">', body)
        self.assert_no_sale(body)

    def test_the_order_search_names_no_customer(self):
        self.sign_in("mustafa", "orders", "beyond_sales", "print_labels", "packing_only")
        resp = self.client.get("/search/", {"q": "DK0000901", "type": "orders"})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("DK0000901", body)
        self.assert_no_sale(body)

    def test_staff_see_the_list_as_before(self):
        self.sign_in("zeynep", "orders", "beyond_sales", "prices_customers", "view_profit")
        body = self.list_page().content.decode()
        self.assertIn("DK0000901", body)
        self.assertIn("Zircon Buyer Ltd", body)
        self.assertTrue(any(f in body for f in ("1,234.56", "1.234,56", "1234.56")))
        self.assertIn('<div class="num ord-gross-cell">', body)
        self.assertIn(reverse("operating:create_order_page", args=[self.book.pk]), body)
