"""A cancel that would cancel a supplier purchase waits for a book admin
(operating.cancel_approval)."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from authentication.models import Permission
from crm.models import Contact
from notifications.models import Notification
from operating.models import Order, OrderCancelRequest, OrderItem, Warehouse


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class CancelApprovalTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-KRV", name="Karven", type="supplier", default_currency=usd)
        self.wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        customer = Contact.objects.create(name="Oleg Motuzenko")

        users = get_user_model().objects
        self.owner = users.create_superuser(username="owner_ca", password="pw", email="o@c.a")
        self.clerk = users.create_user(username="clerk_ca", password="pw")
        self.clerk.member.books.add(self.book)
        self.book_admin = users.create_user(username="admin_ca", password="pw")
        self.book_admin.member.books.add(self.book)
        self.book_admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])
        # An admin of another book only.
        self.outside_admin = users.create_user(username="outside_ca", password="pw")
        self.outside_admin.member.books.add(Book.objects.create(name="Ergene"))
        self.outside_admin.member.permissions.add(Permission.objects.get(name="admin"))

        self.client.force_login(self.owner)
        plan = {
            "warehouse_id": self.wh.pk, "current_account_id": self.supplier.pk,
            "customer": {"type": "contact", "pk": customer.pk}, "unit": "m", "date": "2026-09-17",
            "products": [{
                "main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                "has_variants": True,
                "variants": [{"name": "G07", "sku": "K24644.G07", "price": "3.50",
                              "currency": "USD", "sale_price": "5.00",
                              "tops": [{"qty": 30, "barcode": ""}]}],
            }],
        }
        r = self.client.post(reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
                             data=json.dumps(plan), content_type="application/json")
        self.purchase = Invoice.objects.get(pk=r.json()["invoice_id"])
        self.order = self.purchase.for_order
        self.detail = reverse("operating:order_detail", args=[self.order.pk])

    def _cancel(self, user, reason="Customer changed their mind"):
        self.client.force_login(user)
        return self.client.post(self.detail, {"action": "update_status",
                                              "order_status": "cancelled",
                                              "cancel_reason": reason})

    def _decide(self, user, decision, note=""):
        self.client.force_login(user)
        req = OrderCancelRequest.objects.get(order=self.order, status="pending")
        return self.client.post(reverse("operating:order_cancel_request_decide", args=[req.pk]),
                                {"decision": decision, "note": note})

    def _status(self):
        self.order.refresh_from_db()
        self.purchase.refresh_from_db()
        return self.order.order_status, self.purchase.status

    # ── Asking ──────────────────────────────────────────────────────
    def test_a_book_admin_cancels_straight_away(self):
        self._cancel(self.book_admin)
        self.assertEqual(self._status(), ("cancelled", "cancelled"))
        self.assertFalse(OrderCancelRequest.objects.exists())

    def test_anyone_else_asks_and_the_admins_are_told(self):
        self._cancel(self.clerk)
        self.assertEqual(self._status(), ("pending", "ordered"))
        req = OrderCancelRequest.objects.get()
        self.assertEqual((req.action, req.status, req.requested_by), ("cancel", "pending", self.clerk))
        self.assertEqual(req.reason, "Customer changed their mind")
        told = set(Notification.objects.filter(notification_type="order_cancel_request")
                   .values_list("recipient__user__username", flat=True))
        self.assertEqual(told, {"owner_ca", "admin_ca"})          # not the other book's admin

    def test_an_admin_of_another_book_asks_too(self):
        self._cancel(self.outside_admin)
        self.assertEqual(self._status(), ("pending", "ordered"))

    def test_an_order_with_nothing_on_its_way_needs_no_approval(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("accounts:purchase_order_confirm", args=[self.purchase.pk]))
        self._cancel(self.clerk)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "cancelled")

    # ── Frozen while it waits ───────────────────────────────────────
    def test_the_order_is_frozen_while_it_waits(self):
        self._cancel(self.clerk)
        self.client.force_login(self.book_admin)
        r = self.client.post(self.detail, {"action": "update_status", "order_status": "packaging"})
        self.assertEqual(self._status(), ("pending", "ordered"))
        item = self.order.items.get()
        r = self.client.post(self.detail, {"action": "update_item", "item_id": item.pk,
                                           "quantity": "10", "price": "5"},
                             HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.status_code, 400)
        r = self.client.get(reverse("operating:edit_order", args=[self.order.pk]))
        self.assertRedirects(r, self.detail, fetch_redirect_response=False)

    def test_only_one_request_at_a_time(self):
        self._cancel(self.clerk)
        self._cancel(self.clerk, reason="Again")
        self.assertEqual(OrderCancelRequest.objects.count(), 1)

    # ── Deciding ────────────────────────────────────────────────────
    def test_approving_cancels_in_the_admins_name(self):
        self._cancel(self.clerk)
        self._decide(self.book_admin, "approve")
        self.assertEqual(self._status(), ("cancelled", "cancelled"))
        req = OrderCancelRequest.objects.get()
        self.assertEqual((req.status, req.decided_by), ("approved", self.book_admin))
        self.assertTrue(Notification.objects.filter(recipient=self.clerk.member).exists())

    def test_rejecting_leaves_the_order_as_it_was(self):
        self._cancel(self.clerk)
        self._decide(self.book_admin, "reject", note="The goods are already shipped to us")
        self.assertEqual(self._status(), ("pending", "ordered"))
        req = OrderCancelRequest.objects.get()
        self.assertEqual((req.status, req.decision_note),
                         ("rejected", "The goods are already shipped to us"))
        # ...and it is no longer frozen.
        self._cancel(self.book_admin)
        self.assertEqual(self._status(), ("cancelled", "cancelled"))

    def test_the_requester_and_other_books_admins_cannot_decide(self):
        self._cancel(self.clerk)
        for user in (self.clerk, self.outside_admin):
            self._decide(user, "approve")
            self.assertEqual(self._status(), ("pending", "ordered"))

    # ── Deleting and removing lines ─────────────────────────────────
    def test_only_the_books_admin_deletes_and_the_purchase_goes_with_it(self):
        # Only admins delete orders (no shared password any more), so a clerk
        # can't start one; the book's admin deletes at once, cancelling the
        # purchase still on its way in.
        url = reverse("operating:delete_order", args=[self.order.pk])
        self.client.force_login(self.clerk)
        self.client.post(url)
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())
        self.assertFalse(OrderCancelRequest.objects.exists())
        self.client.force_login(self.book_admin)
        self.client.post(url)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, "cancelled")

    def test_removing_the_last_line_of_a_purchase_waits(self):
        item = self.order.items.get()
        self.client.force_login(self.clerk)
        r = self.client.post(self.detail, {"action": "remove_item", "item_id": item.pk},
                             HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(r.json()["approval_requested"])
        self.assertTrue(OrderItem.objects.filter(pk=item.pk).exists())
        req = OrderCancelRequest.objects.get()
        self.assertEqual((req.action, req.item_ids), ("remove_lines", [item.pk]))
        self._decide(self.book_admin, "approve")
        self.assertFalse(OrderItem.objects.filter(pk=item.pk).exists())
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, "cancelled")
