"""A client's page lists every variant they bought and what they paid.

One row per variant, last bought first, with parent and variant SKU and the
last price; the row opens onto every sale of it. Cancelled orders are left
out, and a company's page reads the company's orders.

Run with:
    scripts/test_local.sh crm.tests.test_bought_items_card
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem


class BoughtItemsCard(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.firm = Company.objects.create(name="Lugansk Home")
        self.anna = Contact.objects.create(name="Anna Lugansk", company=self.firm)
        self.account = CurrentAccount.objects.create(
            book=self.book, company=self.firm, code="C-1", name="Lugansk Home",
            type="customer", default_currency=self.usd)
        user = User.objects.create_user("firat", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

        self.linen = Product.objects.create(title="Linen Sheer", sku="LINEN", price=1)
        self.white = ProductVariant.objects.create(product=self.linen, variant_sku="LINEN.WHITE")
        self.cream = ProductVariant.objects.create(product=self.linen, variant_sku="LINEN.CREAM")

    def _order(self, number, day, lines, status="pending"):
        order = Order.objects.create(
            order_number=number, current_account=self.account, contact=self.anna,
            company=self.firm, currency=self.usd, order_status=status,
            order_date=datetime.date(2026, 10, day))
        for variant, qty, price in lines:
            OrderItem.objects.create(order=order, product=self.linen, product_variant=variant,
                                     quantity=Decimal(qty), price=Decimal(price))
        return order

    def _rows(self, url_name, pk):
        page = self.client.get(reverse(url_name, kwargs={"pk": pk}))
        return page.context["bought_items"], page.content.decode()

    def test_one_row_per_variant_last_bought_first_with_every_price(self):
        self._order("ORD-1", 1, [(self.white, "100", "4.00"), (self.cream, "50", "4.20")])
        self._order("ORD-2", 9, [(self.white, "30", "4.50")])
        rows, html = self._rows("crm:company_detail", self.firm.pk)

        self.assertEqual([r["variant"] for r in rows], [self.white, self.cream])
        white = rows[0]
        self.assertEqual(white["last"]["price"], Decimal("4.50"))
        self.assertEqual(white["order_count"], 2)
        self.assertEqual(white["quantity"], Decimal("130"))
        self.assertEqual([s["price"] for s in white["sales"]], [Decimal("4.50"), Decimal("4.00")])
        self.assertIn("LINEN.WHITE", html)
        self.assertIn("$4.50", html)
        self.assertIn(">ORD-1<", html)
        self.assertIn("2 orders · 130 m</span>", html)

    def test_cancelled_orders_are_left_out(self):
        self._order("ORD-1", 1, [(self.white, "100", "4.00")])
        self._order("ORD-2", 9, [(self.cream, "30", "4.50")], status="cancelled")
        rows, _html = self._rows("crm:contact_detail", self.anna.pk)
        self.assertEqual([r["variant"] for r in rows], [self.white])
