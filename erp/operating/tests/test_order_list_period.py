"""The orders list opens on this month: this month's orders plus whatever
is still open from before it. Every other order is on the page too, but
hidden (data-out) until the search box finds it, and the tabs count only
the period's.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import Order


class OrderListPeriodTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="TST-078", name="PERAKENDE",
            type="customer", default_currency=usd)
        self.this_month = timezone.localdate().replace(day=1)
        self.last_month = (self.this_month - datetime.timedelta(days=1)).replace(day=1)

        self.current = self._order("DK-NOW", self.this_month, "shipped")
        self.old_shipped = self._order("DK-OLD", self.last_month, "shipped")
        self.old_open = self._order("DK-OPEN", self.last_month, "pending")

        User = get_user_model()
        user = User.objects.create_user("staff", password="pw")
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
        # Past save(), which may stamp its own date and status.
        Order.objects.filter(pk=order.pk).update(order_date=day, order_status=status)
        return order

    def _shown(self, response):
        return {o.order_number for o in response.context["orders"] if o.in_period}

    def test_opens_on_this_month_plus_what_is_still_open(self):
        response = self.client.get(self.url)
        self.assertEqual(self._shown(response), {"DK-NOW", "DK-OPEN"})
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["retail_count"], 2)
        self.assertEqual(response.context["carried_count"], 1)
        self.assertContains(response, "plus 1 open order from earlier")

    def test_an_order_outside_the_period_is_on_the_page_but_hidden(self):
        """Hidden, not absent: the search box has to be able to find it."""
        html = self.client.get(self.url).content.decode()
        hidden = (f'data-order-id="{self.old_shipped.pk}" data-search="'
                  f'{self.old_shipped.pk} DK-OLD PERAKENDE TST-078" data-out')
        self.assertEqual(html.count(hidden), 2)  # All + Retail panes
        self.assertEqual(html.count(" data-out "), 2)

    def test_a_past_month_shows_only_its_own_orders(self):
        response = self.client.get(
            self.url, {"month": self.last_month.strftime("%Y-%m")})
        self.assertEqual(self._shown(response), {"DK-OLD", "DK-OPEN"})
        self.assertEqual(response.context["carried_count"], 0)

    def test_all_time_shows_everything(self):
        response = self.client.get(self.url, {"month": "all"})
        self.assertEqual(self._shown(response), {"DK-NOW", "DK-OLD", "DK-OPEN"})
        self.assertNotContains(response, " data-out ")

    def test_a_month_that_is_not_one_falls_back_to_this_month(self):
        response = self.client.get(self.url, {"month": "soon"})
        self.assertEqual(response.context["period_start"], self.this_month)

    def test_open_orders_lead_the_list_longest_waiting_first(self):
        newer_open = self._order("DK-OPEN-2", self.this_month, "packaging")
        response = self.client.get(self.url, {"month": "all"})
        self.assertEqual(
            [o.order_number for o in response.context["orders"]],
            ["DK-OPEN", "DK-OPEN-2", "DK-OLD", "DK-NOW"])
        html = response.content.decode()
        # One heading per half, in the All and Retail panes.
        self.assertEqual(html.count('class="ord-group" data-group="open"'), 2)
        self.assertEqual(html.count('class="ord-group" data-group="done"'), 2)
        self.assertLess(html.index('data-group="open"'),
                        html.index(f'data-order-id="{newer_open.pk}"'))
