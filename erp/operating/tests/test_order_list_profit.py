"""The orders list's gross profit: a shipped order at what its goods went
out at, and a total of the rows on screen that only an admin sees.

Run with:
    python manage.py test operating.tests.test_order_list_profit
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from accounting.services_ledger import ensure_chart
from authentication.models import Permission
from marketing.models import Product
from operating.models import (Order, OrderItem, StockMovement, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


class OrderListProfitTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        ensure_chart()
        account = CurrentAccount.objects.create(
            book=self.book, code="TST-1", name="Hanefi", type="customer",
            default_currency=usd)
        warehouse = Warehouse.objects.create(name="Laleli", accounting_book=self.book)
        self.shelf = WarehouseProduct.objects.create(
            warehouse=warehouse, name="seta", sku="S1",
            quantity=Decimal("100"), cost_usd=Decimal("4.00"))
        # The roll went out at 4.00 a meter; the same goods cost 10.00 today.
        self.roll = WarehouseProductItem.objects.create(
            product=self.shelf, quantity=Decimal("100"),
            quantity_remaining=Decimal("100"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4.00"))
        product = Product.objects.create(title="Seta", featured=False, unit="meter")
        self.variant = product.variants.create(variant_sku="SETA", variant_cost=Decimal("10"))

        def order(number, status):
            o = Order.objects.create(order_number=number, current_account=account,
                                     currency=usd)
            OrderItem.objects.create(order=o, product=product, product_variant=self.variant,
                                     quantity=Decimal("25"), price=Decimal("12"))
            Order.objects.filter(pk=o.pk).update(order_status=status)
            return o

        self.shipped = order("DK-SHIP", "shipped")
        StockMovement.objects.create(
            product=self.shelf, stock_item=self.roll, movement_type="out",
            quantity=Decimal("25"), reason="Order ship", order=self.shipped)
        self.open = order("DK-OPEN", "pending")
        self.cancelled = order("DK-CANC", "cancelled")
        self.url = reverse("operating:order_list_scoped", kwargs={"book_id": self.book.pk})

    def _login(self, *permissions, superuser=False):
        User = get_user_model()
        if superuser:
            user = User.objects.create_superuser("boss", "b@o.ss", "pw")
        else:
            user = User.objects.create_user("staff", password="pw")
        for name in permissions:
            perm, _ = Permission.objects.get_or_create(name=name)
            user.member.permissions.add(perm)
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _profits(self, response):
        return {o.order_number: o.list_gross_profit for o in response.context["orders"]}

    def test_a_shipped_order_costs_what_its_goods_went_out_at(self):
        self._login(superuser=True)
        profits = self._profits(self.client.get(self.url, {"month": "all"}))
        # 25 m sold at 12.00 = 300.00; the roll went out at 25 x 4.00 = 100.00.
        self.assertEqual(profits["DK-SHIP"], Decimal("200.00"))
        # Nothing has left for an open order: today's 10.00 a meter.
        self.assertEqual(profits["DK-OPEN"], Decimal("50.00"))

    def test_putting_the_goods_back_takes_their_cost_off(self):
        StockMovement.objects.create(
            product=self.shelf, stock_item=self.roll, movement_type="in",
            quantity=Decimal("5"), reason="Order edit", order=self.shipped)
        self._login(superuser=True)
        profits = self._profits(self.client.get(self.url, {"month": "all"}))
        self.assertEqual(profits["DK-SHIP"], Decimal("220.00"))   # cost 20 x 4.00

    def test_an_admin_sees_the_total_and_the_rows_it_adds(self):
        self._login("admin", "view_profit")
        response = self.client.get(self.url, {"month": "all"})
        self.assertContains(response, 'id="ord-gp-total"')
        html = response.content.decode()
        # No contact or company, so each row is in the All pane only.
        self.assertEqual(html.count('data-gp="200.00" data-ccy="USD" data-sym="$"'), 1)
        self.assertEqual(html.count('data-gp="50.00"'), 1)
        # A cancelled order made no sale, so the total leaves it out.
        self.assertEqual(html.count("data-gp="), 2)
        self.assertRegex(html, rf'data-order-id="{self.cancelled.pk}" data-search="[^"]*">')

    def test_profit_without_admin_shows_the_column_but_not_the_total(self):
        self._login("view_profit")
        response = self.client.get(self.url, {"month": "all"})
        self.assertNotContains(response, 'id="ord-gp-total"')
        self.assertNotContains(response, "data-gp=")
        self.assertContains(response, 'class="num ord-gross-cell"')
