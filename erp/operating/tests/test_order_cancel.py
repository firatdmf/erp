"""Cancelling an order: a confirmed, reasoned, one-way step.

The order page has a "Cancel order" button whose dialog insists on a
reason; the reason lands in the change history. A completed order can't
be cancelled in one step — it is re-opened first. A cancelled order keeps
its lines on the page, struck through.
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
from operating.models import Order, OrderChange, OrderItem
from operating.views_warehouse import apply_order_status_change


class OrderCancelBase(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.book = Book.objects.create(name="Laleli Fabric")
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-401", name="Oleg", type="customer",
            default_currency=self.usd)
        self.product = Product.objects.create(title="Velvet Moss", sku="KZL000401", price=10)

        self.user = User.objects.create_user("staff_cancel", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.client.force_login(self.user)

    def order(self, status="pending"):
        order = Order.objects.create(
            order_number=f"DK0000{Order.objects.count() + 401}",
            current_account=self.account, order_status=status)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("40.00"), price=Decimal("3.25"))
        return order

    def detail_url(self, order):
        return reverse("operating:order_detail", kwargs={"pk": order.pk})

    def cancel(self, order, reason="Customer changed their mind"):
        data = {"action": "update_status", "order_status": "cancelled"}
        if reason is not None:
            data["cancel_reason"] = reason
        return self.client.post(self.detail_url(order), data)


class CancellingFromTheOrderPage(OrderCancelBase):

    def test_an_open_order_is_cancelled_and_the_reason_logged(self):
        order = self.order()
        self.cancel(order)
        order.refresh_from_db()
        self.assertEqual(order.order_status, "cancelled")
        log = OrderChange.objects.get(order=order, field="cancel_reason")
        self.assertEqual(log.new_value, "Customer changed their mind")
        self.assertEqual(log.created_by, self.user)

    def test_no_reason_no_cancel(self):
        order = self.order()
        for reason in (None, "", "   "):
            self.cancel(order, reason=reason)
            order.refresh_from_db()
            self.assertEqual(order.order_status, "pending")
        self.assertFalse(OrderChange.objects.filter(field="cancel_reason").exists())

    def test_a_completed_order_is_refused(self):
        order = self.order(status="shipped")
        self.cancel(order)
        order.refresh_from_db()
        self.assertEqual(order.order_status, "shipped")
        self.assertFalse(OrderChange.objects.filter(field="cancel_reason").exists())

    def test_the_funnel_refuses_every_completed_status(self):
        for status in ("shipped", "in_transit", "out_for_delivery", "delivered"):
            order = self.order(status=status)
            self.assertEqual(
                apply_order_status_change(order, "cancelled", user=self.user),
                (False, "cancel_requires_reopen"))
            order.refresh_from_db()
            self.assertEqual(order.order_status, status)

    def test_a_re_opened_order_can_be_cancelled(self):
        order = self.order(status="packaging")
        self.assertEqual(apply_order_status_change(order, "cancelled", user=self.user),
                         (True, None))


class TheOrderPage(OrderCancelBase):

    def test_an_open_order_offers_the_button_and_no_one_click_cancel(self):
        resp = self.client.get(self.detail_url(self.order()))
        self.assertContains(resp, 'id="od-cancel-order-btn"')
        self.assertContains(resp, 'id="odCancelModal"')
        self.assertNotContains(resp, 'data-status="cancelled"')

    def test_a_completed_order_offers_no_cancel(self):
        resp = self.client.get(self.detail_url(self.order(status="shipped")))
        self.assertNotContains(resp, 'id="od-cancel-order-btn"')
        self.assertNotContains(resp, 'id="odCancelModal"')

    def test_a_sales_rep_gets_no_cancel(self):
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)
        resp = self.client.get(self.detail_url(self.order()))
        self.assertNotContains(resp, 'id="od-cancel-order-btn"')

    def test_a_cancelled_order_keeps_its_lines_struck_through(self):
        order = self.order()
        self.cancel(order)
        resp = self.client.get(self.detail_url(order))
        self.assertContains(resp, ' od-prods-cancelled">')
        self.assertContains(resp, 'class="od-totals od-totals-cancelled"')
        self.assertContains(resp, "Velvet Moss")
        self.assertContains(resp, 'data-item-row="%d"' % order.items.get().pk)
        self.assertNotContains(resp, 'id="od-cancel-order-btn"')
        self.assertNotContains(resp, 'id="od-complete-btn"')

    def test_an_open_order_is_not_struck_through(self):
        resp = self.client.get(self.detail_url(self.order()))
        self.assertNotContains(resp, ' od-prods-cancelled">')
        self.assertNotContains(resp, 'class="od-totals od-totals-cancelled"')
