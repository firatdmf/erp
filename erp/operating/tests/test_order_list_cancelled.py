"""A cancelled order is never completed: the orders list files it under its
own Cancelled heading, after the completed ones, struck through and grayed
out."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import Order


class OrderListCancelledTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="TST-078", name="PERAKENDE",
            type="customer", default_currency=usd)
        today = timezone.localdate()
        # Cancelled made last, so newest-first alone would put it on top.
        self.open = self._order("DK-OPEN", today, "pending")
        self.shipped = self._order("DK-SHIP", today, "shipped")
        self.cancelled = self._order("DK-CANC", today, "cancelled")

        user = get_user_model().objects.create_user("staff", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)
        self.url = reverse("operating:order_list_scoped",
                           kwargs={"book_id": self.book.pk})

    def _order(self, number, day, status):
        order = Order.objects.create(
            order_number=number, current_account=self.account,
            is_retail_order=True, order_date=day)
        Order.objects.filter(pk=order.pk).update(order_date=day, order_status=status)
        return order

    def test_cancelled_has_its_own_group_after_completed(self):
        response = self.client.get(self.url)
        groups = [(o.order_number, o.list_group) for o in response.context["orders"]]
        self.assertEqual(groups, [("DK-OPEN", "open"), ("DK-SHIP", "done"),
                                  ("DK-CANC", "cancelled")])
        self.assertContains(response, 'class="ord-group" data-group="cancelled"')

    def test_only_the_cancelled_row_is_struck_through(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'is-cancelled" data-group="cancelled" data-order-id="{self.cancelled.pk}"', html)
        self.assertEqual(html.count('class="ord-row is-cancelled"'), 2)  # All + Retail panes
