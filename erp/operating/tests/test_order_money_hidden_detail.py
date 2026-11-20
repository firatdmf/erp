"""The order page for whoever packs and ships without Prices and customers.

Operations hold Orders but not Prices and customers: the order page shows
them the goods, the packages, the status and shipping controls and where
the order goes — and nothing of the sale. Not hidden in the page but
absent from it: no price, total or customer in the HTML, its data
attributes or its scripts. A role with the permission sees the page as
before.

Run with:
    python manage.py test operating.tests.test_order_money_hidden_detail
"""
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Contact
from crm.tests import works_in_a_book
from marketing.models import Product
from operating.models import Order, OrderItem

# What a member of the Operations role holds: its grants, and the
# restriction of the one it leaves out (authentication.member_roles).
OPERATIONS = ("orders", "beyond_sales", "print_labels", "packing_only")
STAFF = ("orders", "beyond_sales", "prices_customers")


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.test/qr.png")
class OrderPageWithoutPricesAndCustomers(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.test/qr.png")
    def setUp(self, _upload):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.buyer = Contact.objects.create(name="Zircon Buyer Ltd", email=["buyer@zircon.test"])
        self.order = self.order_in(self.ergene, "DK0000901", "KZL000901", Decimal("1234.56"))

    def order_in(self, book, number, sku, price, **fields):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{uuid4().hex[:8]}", name="Zircon Buyer Ltd",
            type="customer", default_currency=self.usd)
        order = Order.objects.create(
            order_number=number, current_account=account, contact=self.buyer,
            status="pending", delivery_address="Quartz Street 9",
            delivery_city="Tekirdağ", **fields)
        product = Product.objects.create(title=f"Crepe {sku}", sku=sku)
        OrderItem.objects.create(
            order=order, product=product,
            product_variant=product.variants.create(
                variant_sku=sku, variant_price=10, variant_cost=Decimal("1.37")),
            quantity=Decimal("2.00"), price=price)
        return order

    def sign_in(self, name, grants, books):
        user = User.objects.create_user(name, password="pw")
        for book in books:
            works_in_a_book(user, book.name)
        for grant in grants:
            user.member.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        self.client.force_login(user)
        return user

    def page(self, order=None):
        response = self.client.get(reverse("operating:order_detail", args=[(order or self.order).pk]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def assert_no_sale(self, html, *figures):
        for leak in ("Zircon Buyer Ltd", "buyer@zircon.test", "Grand total",
                     "Current account", "Get invoice") + figures:
            with self.subTest(leak=leak):
                self.assertNotIn(leak, html)

    def test_operations_see_the_goods_and_where_they_go(self, _upload):
        self.sign_in("mustafa", OPERATIONS, [self.ergene])
        html = self.page()
        for shown in ("DK0000901", "KZL000901", "Quartz Street 9", 'id="od-complete-btn"',
                      reverse("operating:order_pack_scan", args=[self.order.pk])):
            with self.subTest(shown=shown):
                self.assertIn(shown, html)
        self.assert_no_sale(html, "1,234.56", "1234.56", "2,469.12", "2469.12", "1.37")

    def test_staff_still_see_the_sale(self, _upload):
        self.sign_in("zeynep", STAFF, [self.ergene])
        html = self.page()
        for shown in ("Zircon Buyer Ltd", "1,234.56", "2,469.12", "Grand total"):
            with self.subTest(shown=shown):
                self.assertIn(shown, html)

    def test_operations_cannot_change_lines_or_customer_inline(self, _upload):
        self.sign_in("mustafa", OPERATIONS, [self.ergene])
        item = self.order.items.get()
        response = self.client.post(
            reverse("operating:order_detail", args=[self.order.pk]),
            {"action": "update_item", "item_id": item.pk, "field": "price", "value": "1"})
        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("1234.56"))

    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.test/qr.png")
    def test_a_split_order_shows_no_money_either(self, _upload, _upload2):
        group = uuid4()
        Order.objects.filter(pk=self.order.pk).update(split_group=group)
        self.order_in(self.laleli, "DK0000902", "KZL000902", Decimal("4321.98"), split_group=group)
        self.sign_in("mustafa", OPERATIONS, [self.ergene, self.laleli])
        html = self.page()
        self.assertIn("KZL000902", html)
        self.assert_no_sale(html, "1,234.56", "4,321.98", "4321.98", "Subtotal")
