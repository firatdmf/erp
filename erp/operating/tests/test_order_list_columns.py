"""The orders list carries the order's primary key in its own column,
and gross profit in its own column — a column only the view_profit grant
gets, not even as an empty cell, since the header would still name it.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem


class OrderListColumnsTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=self.book, code="TST-078", name="PERAKENDE",
            type="customer", default_currency=usd)
        product = Product.objects.create(
            title="Bamboo Plise", sku="TTEMPILISE", featured=False)
        variant = ProductVariant.objects.create(
            product=product, variant_sku="K24649.G34")
        self.order = Order.objects.create(
            order_number="DK-501", current_account=account,
            is_retail_order=True)
        OrderItem.objects.create(
            order=self.order, product=product, product_variant=variant,
            quantity=Decimal("12"), price=Decimal("4.50"))

        User = get_user_model()
        self.user = User.objects.create_user("staff", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.view_profit, _ = Permission.objects.get_or_create(name="view_profit")
        self.user.member.permissions.add(self.view_profit)
        self.client.force_login(self.user)
        self.url = reverse("operating:order_list_scoped",
                           kwargs={"book_id": self.book.pk})

    def _make_rep(self):
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)
        self.user.member.permissions.remove(self.view_profit)

    def test_every_pane_shows_the_pk_column(self):
        html = self.client.get(self.url).content.decode()
        # All + Retail panes each carry the header and the row cell.
        self.assertEqual(html.count(">ID</span>"), 2)
        self.assertEqual(
            html.count(f'<span class="ord-pk">{self.order.pk}</span>'), 2)

    def test_the_grant_gets_a_gross_profit_column(self):
        html = self.client.get(self.url).content.decode()
        self.assertEqual(html.count(">Gross profit</span>"), 2)
        self.assertEqual(html.count('class="num ord-gross-cell"'), 2)
        # The grid carries a track for it, just before Status.
        self.assertIn(" 110px 150px 24px;", html)

    def test_without_the_grant_there_is_no_gross_profit_column_at_all(self):
        """Any member, not just the sales rep: the gate is the grant."""
        self.user.member.permissions.remove(self.view_profit)
        self._assert_no_profit_column(self.client.get(self.url).content.decode())

    def test_a_sales_rep_gets_no_gross_profit_column_at_all(self):
        self._make_rep()
        self._assert_no_profit_column(self.client.get(self.url).content.decode())

    def test_a_superuser_needs_no_grant(self):
        self.user.member.permissions.remove(self.view_profit)
        self.user.is_superuser = True
        self.user.save()
        html = self.client.get(self.url).content.decode()
        self.assertEqual(html.count(">Gross profit</span>"), 2)

    def _assert_no_profit_column(self, html):
        self.assertNotIn("Gross profit", html)
        self.assertNotIn('class="num ord-gross-cell"', html)
        # Not even an empty track: the grid is one column narrower.
        self.assertNotIn(" 110px 150px 24px;", html)
        self.assertIn(" 150px 24px;", html)
        # The pk column is not a secret.
        self.assertIn(f'<span class="ord-pk">{self.order.pk}</span>', html)
