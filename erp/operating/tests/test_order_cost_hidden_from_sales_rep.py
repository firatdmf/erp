"""A sales rep reads an order's prices, never what it cost us.

Cost, COGS and profit are the margin. The order page draws them for
staff; for a sales rep it draws none of them, and the edit endpoints
that refresh them without a reload send none back either — hiding the
rows while the JSON still carried the numbers would hide nothing.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from marketing.models import Product
from operating.models import Order, OrderItem


class OrderCostIsHiddenFromSalesRep(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-301", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(
            order_number="DK0000301", current_account=account, order_status="pending")
        product = Product.objects.create(title="Crepe", sku="KZL000315",
                                         price=10, cost=Decimal("1.37"))
        self.item = OrderItem.objects.create(
            order=self.order, product=product,
            quantity=Decimal("100.00"), price=Decimal("2.50"))

        self.user = User.objects.create_user("rep_test", password="pw")
        self.user.member.books.add(book)
        self.user.member.default_book = book
        self.user.member.save()
        self.client.force_login(self.user)
        self.url = reverse("operating:order_detail", kwargs={"pk": self.order.pk})

    def _make_rep(self):
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)

    def test_staff_still_see_cost_and_profit(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Total cost (COGS)")
        self.assertContains(resp, 'data-unit-cost="1.37')
        self.assertContains(resp, "$1.37")

    def test_a_sales_rep_sees_neither(self):
        self._make_rep()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Total cost (COGS)")
        self.assertNotContains(resp, "data-order-profit style")
        self.assertNotContains(resp, 'data-unit-cost="1.37')
        self.assertNotContains(resp, "$1.37")
        # The price is still theirs to read.
        self.assertContains(resp, "$2.50")

    def test_the_refresh_snapshot_carries_no_profit_for_a_sales_rep(self):
        """Scanning rolls onto an order (pack/add, which the role may post)
        answers with this snapshot, so it is the one that must be empty."""
        from operating.views import _order_profit_snapshot
        self.assertIsNotNone(_order_profit_snapshot(self.order, self.user))
        self._make_rep()
        self.assertIsNone(_order_profit_snapshot(self.order, self.user))

    def test_the_order_list_shows_a_sales_rep_no_profit(self):
        url = reverse("operating:order_list_scoped", args=[self.order.current_account.book_id])
        self.assertContains(self.client.get(url), "Gross profit (internal)")
        self._make_rep()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Gross profit (internal)")

    def test_analytics_shows_a_sales_rep_no_profit_or_cogs(self):
        url = reverse("operating:order_analytics")
        self.assertContains(self.client.get(url), "Cost (COGS)")
        self._make_rep()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Cost (COGS)")
        self.assertNotContains(resp, "an-kpi profit")
