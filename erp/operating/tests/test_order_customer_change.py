# to run this test, use the command:
# python manage.py test operating.tests.test_order_customer_change

"""Changing an order's customer moves its sale to the new customer's account.

post_order_movement updated an existing movement's amount, date and book
in place but never its account. The order edit form re-resolves the
current account and then calls it, so a customer swap left the sale on
the old account: Order 307 was moved from SVETLANA STRATAN MOLDOVA to
SVETA VİLNUS KARGO and kept billing Moldova.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import post_order_movement
from crm.models import Company
from marketing.models import Product
from operating.models import Order, OrderItem


class OrderCustomerChangeTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.wrong_co = Company.objects.create(name="Moldova")
        self.right_co = Company.objects.create(name="Vilnius")
        self.wrong = CurrentAccount.objects.create(
            book=self.book, code="C-MD", name="Moldova", type="customer",
            company=self.wrong_co, default_currency=self.usd)
        self.right = CurrentAccount.objects.create(
            book=self.book, code="C-LT", name="Vilnius", type="customer",
            company=self.right_co, default_currency=self.usd)
        self.product = Product.objects.create(title="Krep", sku="KRP", featured=False)
        self.member = getattr(
            get_user_model().objects.create_superuser("firat_cc", "a@b.c", "pw"), "member", None)

    def test_the_sale_follows_the_order_to_its_new_customer(self):
        order = Order.objects.create(company=self.wrong_co, current_account=self.wrong)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("100"), price=Decimal("2.00"))
        post_order_movement(order, member=self.member)
        self.wrong.refresh_from_db()
        self.assertEqual(self.wrong.cached_balance, Decimal("200.00"))

        # What the order edit form does on a customer swap.
        order.company = self.right_co
        order.current_account = self.right
        order.save()
        post_order_movement(order, member=self.member)

        sales = CurrentAccountMovement.objects.filter(movement_type="order_sale")
        self.assertEqual([mv.current_account_id for mv in sales], [self.right.pk])
        self.wrong.refresh_from_db()
        self.right.refresh_from_db()
        self.assertEqual(self.wrong.cached_balance, Decimal("0.00"))
        self.assertEqual(self.right.cached_balance, Decimal("200.00"))
