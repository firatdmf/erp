"""An order split across books is one order on screen.

Two orders in the books — one per book, each billing its own account — and
one order on the page: named by both numbers, listing every half's lines and
totals. Whoever may open one half sees the whole order, so a sales rep who
holds only Laleli can follow the Ergene half of her customer's order — its
lines, prices and total — without ever reaching the Ergene account.

Run with:
    python manage.py test operating.tests.test_split_order_page
"""
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderItem


class SplitOrderPage(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        customer = Contact.objects.create(name="Anna Lugansk")
        group = uuid.uuid4()
        self.laleli_half = self._half(self.laleli, "ORD-2026-000023", customer, group, usd,
                                      "Krep", Decimal("2.50"))
        self.ergene_half = self._half(self.ergene, "ORD-2026-000024", customer, group, usd,
                                      "Tul Ergene", Decimal("7.25"))

        self.user = User.objects.create_user("ruzana", password="pw")
        self.user.member.books.add(self.laleli)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.user.member.permissions.add(Permission.objects.get_or_create(name="sales_rep")[0])
        self.client.force_login(self.user)

    def _half(self, book, number, customer, group, currency, title, price):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{book.pk}", name=f"Anna ({book.name})", type="customer",
            contact=customer, default_currency=currency)
        order = Order.objects.create(order_number=number, current_account=account,
                                     contact=customer, currency=currency, split_group=group)
        OrderItem.objects.create(order=order, quantity=Decimal("10"), price=price,
                                 product=Product.objects.create(title=title, sku=title[:6], price=1))
        return order

    def _page(self, order):
        return self.client.get(reverse("operating:order_detail", kwargs={"pk": order.pk}))

    def test_the_page_is_named_by_both_halves(self):
        resp = self._page(self.laleli_half)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ORD-2026-000023 &amp; ORD-2026-000024")

    def test_the_rep_sees_the_other_book_s_lines_prices_and_total(self):
        resp = self._page(self.laleli_half)
        self.assertContains(resp, "Tul Ergene")
        self.assertContains(resp, "$7.25")
        self.assertContains(resp, "$72.50")          # the Ergene half's total
        self.assertContains(resp, "Combined total")
        self.assertContains(resp, "$97.50")          # 25.00 + 72.50

    def test_but_not_the_other_book_s_account(self):
        resp = self._page(self.laleli_half)
        self.assertNotContains(resp, "Anna (Ergene Fabric)")
        self.assertNotContains(resp, "Open this half")

    def test_opening_the_other_half_leads_to_the_one_she_may_open(self):
        resp = self._page(self.ergene_half)
        self.assertRedirects(resp, reverse("operating:order_detail",
                                           kwargs={"pk": self.laleli_half.pk}))

    def test_an_unsplit_order_of_another_book_stays_hidden(self):
        account = CurrentAccount.objects.create(
            book=self.ergene, code="C-X", name="Someone", type="customer",
            default_currency=CurrencyCategory.objects.get(code="USD"))
        other = Order.objects.create(order_number="ORD-2026-000099", current_account=account)
        self.assertEqual(self._page(other).status_code, 404)

    def test_someone_holding_both_books_can_open_either_half(self):
        self.user.member.books.add(self.ergene)
        resp = self._page(self.laleli_half)
        self.assertContains(resp, "Open this half")
        self.assertEqual(self._page(self.ergene_half).status_code, 200)

    def test_the_order_list_tags_the_split(self):
        resp = self.client.get(reverse("operating:order_list_scoped", kwargs={"book_id": self.laleli.pk}))
        self.assertContains(resp, "Split with")
        self.assertContains(resp, "Ergene Fabric")
