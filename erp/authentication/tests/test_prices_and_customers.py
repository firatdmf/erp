"""Prices and customers: a role with Orders but without it (Operations)
works orders without their money or customer. See erp.roles.sees_order_money.
"""
import importlib
from uuid import uuid4

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.member_roles import put_in_role
from authentication.models import Member, Permission, Role
from erp.roles import sees_order_money
from operating.models import Order


class PricesAndCustomersTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Ergene Fabric")
        account = CurrentAccount.objects.create(
            book=self.book, code=f"C-{uuid4().hex[:8]}", name="Karven", type="customer",
            default_currency=CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(order_number="ORD-2026-000801",
                                          order_status="packaging", current_account=account)

    def role(self, name, *grants):
        role = Role.objects.create(name=name)
        for grant in grants:
            role.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        return role

    def sign_in(self, role):
        user = User.objects.create_user(f"u{uuid4().hex[:6]}", password="pw")
        user.member.books.add(self.book)
        put_in_role(user.member, role)
        self.client.force_login(user)
        return user

    def test_operations_open_the_order_but_not_its_money_pages(self):
        user = self.sign_in(self.role("Operations", "orders", "beyond_sales", "print_labels"))
        self.assertFalse(sees_order_money(user))
        pk = self.order.pk
        self.assertEqual(self.client.get(reverse("operating:order_detail", args=[pk])).status_code, 200)
        for name in ("order_print", "order_invoice", "order_excel", "order_customer_card",
                     "order_changes", "edit_order"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"operating:{name}", args=[pk])).status_code, 403)
        for name in ("create_order", "order_analytics"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"operating:{name}")).status_code, 403)

    def test_the_menu_drops_what_needs_prices_and_customers(self):
        self.sign_in(self.role("Operations", "orders", "beyond_sales", "print_labels"))
        page = self.client.get(reverse("operating:warehouse_list")).content.decode()
        self.assertNotIn(reverse("operating:order_analytics"), page)
        self.assertNotIn("openOrderSidebar()", page)
        self.assertIn(reverse("operating:order_list"), page)

    def test_a_role_with_it_sees_everything(self):
        user = self.sign_in(self.role("Staff", "orders", "beyond_sales", "prices_customers"))
        self.assertTrue(sees_order_money(user))
        self.assertEqual(self.client.get(
            reverse("operating:order_customer_card", args=[self.order.pk])).status_code, 200)
        page = self.client.get(reverse("operating:warehouse_list")).content.decode()
        self.assertIn(reverse("operating:order_analytics"), page)

    def test_the_seed_changes_no_ones_view_of_an_order(self):
        staff = self.role("Staff", "orders", "beyond_sales")
        warehouse = self.role("Warehouse only", "beyond_sales")
        in_staff = User.objects.create_user("cuma", password="pw").member
        put_in_role(in_staff, staff)
        in_warehouse = User.objects.create_user("mustafa", password="pw").member
        put_in_role(in_warehouse, warehouse)
        loose = User.objects.create_user("loose", password="pw").member
        Permission.objects.filter(name__in=("prices_customers", "packing_only")).delete()

        importlib.import_module(
            "authentication.migrations.0037_seed_prices_and_customers").seed(apps, None)

        # A role with Orders gets the permission, and its members keep money.
        self.assertTrue(staff.permissions.filter(name="prices_customers").exists())
        self.assertTrue(sees_order_money(Member.objects.get(pk=in_staff.pk)))
        # A role without Orders is restricted, and saw no order anyway.
        self.assertFalse(warehouse.permissions.filter(name="prices_customers").exists())
        self.assertFalse(sees_order_money(Member.objects.get(pk=in_warehouse.pk)))
        # A member in no role is left as they were: a role's, never one person's.
        self.assertFalse(Member.objects.get(pk=loose.pk).permissions.exists())
        self.assertTrue(sees_order_money(Member.objects.get(pk=loose.pk)))
