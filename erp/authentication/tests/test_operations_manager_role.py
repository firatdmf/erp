"""An operations manager runs the warehouse and has no business with orders.

Asserted over HTTP, like the sales-rep tests beside it, so a middleware left
out of settings would fail them. See erp.roles.ORDER_PREFIXES.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase

from authentication.models import Member, Permission
from crm.tests import works_in_a_book
from erp.roles import is_order_path


class OperationsManagerRoleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mustafa_test", password="pw-for-test")
        self.book = works_in_a_book(self.user)
        member, _ = Member.objects.get_or_create(user=self.user)
        member.permissions.add(Permission.objects.get_or_create(name="manager")[0])
        self.client = Client()
        self.client.force_login(self.user)

    def test_every_order_door_is_closed(self):
        from operating.models import Order

        order = Order.objects.create(order_status="pending", created_by=self.user)
        for path in ("/operating/orders/",
                     f"/operating/books/{self.book.pk}/orders/",
                     f"/operating/books/{self.book.pk}/orders/create/",
                     "/operating/orders/create",
                     f"/operating/orders/{order.pk}/",
                     f"/operating/orders/edit/{order.pk}/",
                     f"/operating/orders/{order.pk}/pack/",
                     f"/operating/orders/{order.pk}/print/",
                     "/operating/orders/analytics/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post("/operating/orders/create", {}).status_code, 403)
        self.assertFalse(Order.objects.exclude(pk=order.pk).exists())

    def test_the_warehouse_stays_open(self):
        self.assertEqual(self.client.get("/operating/warehouses/").status_code, 200)

    def test_no_order_door_is_shown(self):
        page = self.client.get("/operating/warehouses/").content.decode()
        # Links and buttons, not the path itself: base.html defines
        # openOrderSidebar for every page, and its body names the form.
        for door in ('href="/operating/orders/', "openOrderSidebar()",
                     "/operating/orders/analytics/", 'data-tab="orders"'):
            with self.subTest(door=door):
                self.assertNotIn(door, page)

    def test_the_search_returns_no_orders(self):
        results = self.client.get("/search/?q=ORD&type=all").json()["results"]
        self.assertFalse([r for r in results if is_order_path(r.get("url") or "")])

    def test_purchase_orders_are_not_orders(self):
        # Procurement is warehouse work; only the "/operating/orders" prefix
        # and the order APIs are closed.
        self.assertFalse(is_order_path("/operating/procurement/orders/"))
        self.assertTrue(is_order_path("/operating/orders"))

    def test_everyone_else_still_sees_orders(self):
        other = User.objects.create_user("cuma_test", password="pw-for-test")
        works_in_a_book(other)
        client = Client()
        client.force_login(other)
        self.assertEqual(client.get("/operating/orders/").status_code, 302)
        self.assertIn("/operating/orders/", client.get("/operating/warehouses/").content.decode())

    def test_superuser_is_never_held(self):
        boss = User.objects.create_superuser("boss_ops_test", password="pw-for-test")
        Member.objects.get_or_create(user=boss)[0].permissions.add(
            Permission.objects.get(name="manager"))
        client = Client()
        client.force_login(boss)
        self.assertNotEqual(client.get("/operating/orders/").status_code, 403)
