"""A customer's order card lists what each order comes to.

Its grand total — delivery and discounts in — as the order's own page says
it; and an order split across books is one row, both numbers on it, its
halves' totals added up.

Run with:
    python manage.py test crm.tests.test_order_history_card
"""
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderAdjustment, OrderItem


class OrderHistoryCard(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.anna = Contact.objects.create(name="Anna Lugansk")
        self.user = User.objects.create_user("firat", password="pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _order(self, book, number, price, group=None):
        account, _ = CurrentAccount.objects.get_or_create(
            book=book, contact=self.anna,
            defaults={"code": f"C-{book.pk}", "name": f"Anna ({book.name})",
                      "type": "customer", "default_currency": self.usd})
        order = Order.objects.create(order_number=number, current_account=account,
                                     contact=self.anna, currency=self.usd, split_group=group)
        OrderItem.objects.create(order=order, quantity=Decimal("10"), price=Decimal(price),
                                 product=Product.objects.create(title=number, sku=number, price=1))
        return order

    def _card(self):
        page = self.client.get(reverse("crm:contact_detail", kwargs={"pk": self.anna.pk}))
        return page, page.content.decode()

    def test_a_row_shows_the_order_s_grand_total(self):
        order = self._order(self.laleli, "ORD-2026-000050", "2.50")
        OrderAdjustment.objects.create(order=order, label="Delivery", amount=Decimal("5"))
        _page, html = self._card()
        self.assertIn("$30.00", html)  # 25.00 + 5.00 delivery

    def test_a_split_order_is_one_row_with_both_numbers_and_one_total(self):
        group = uuid.uuid4()
        laleli_half = self._order(self.laleli, "ORD-2026-000023", "2.50", group)
        ergene_half = self._order(self.ergene, "ORD-2026-000024", "7.25", group)
        page, html = self._card()
        self.assertEqual(len(page.context["orders"]), 1)
        self.assertIn(">ORD-2026-000023<", html)
        self.assertIn(">ORD-2026-000024<", html)
        self.assertIn("$97.50", html)  # 25.00 + 72.50
        # Ticking it prints both halves.
        self.assertIn(f'value="{ergene_half.pk},{laleli_half.pk}"', html)

    def test_one_who_holds_one_book_still_sees_the_whole_order_but_prints_their_half(self):
        group = uuid.uuid4()
        laleli_half = self._order(self.laleli, "ORD-2026-000023", "2.50", group)
        self._order(self.ergene, "ORD-2026-000024", "7.25", group)
        self.user.member.books.remove(self.ergene)
        _page, html = self._card()
        self.assertIn("$97.50", html)
        self.assertIn(f'value="{laleli_half.pk}"', html)
