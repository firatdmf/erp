"""Accounts and customers: a role without it (Operations) runs warehouses
and purchases without the ledger or the customer lists. See
erp.roles.ACCOUNTS_PREFIXES. Also: order search answers with the orders
of the viewer's own books.
"""
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.member_roles import put_in_role
from authentication.models import Permission, Role
from erp.roles import is_accounts_path, sees_accounts
from operating.models import Order


class AccountsAndCustomersTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Ergene Fabric")
        self.other = Book.objects.create(name="Laleli Fabric")
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.account = self.account_in(self.book)

    def account_in(self, book):
        return CurrentAccount.objects.create(
            book=book, code=f"C-{uuid4().hex[:8]}", name="Zircon Buyer Ltd",
            type="customer", default_currency=self.usd)

    def sign_in(self, *grants):
        role = Role.objects.create(name=f"R{uuid4().hex[:6]}")
        for grant in grants:
            role.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        user = User.objects.create_user(f"u{uuid4().hex[:6]}", password="pw")
        user.member.books.add(self.book)
        put_in_role(user.member, role)
        self.client.force_login(user)
        return user

    def operations(self):
        return self.sign_in("orders", "beyond_sales", "print_labels")

    def test_operations_are_kept_out_of_the_ledger_and_the_crm(self):
        user = self.operations()
        self.assertFalse(sees_accounts(user))
        b = self.book.pk
        for path in (reverse("accounts:legacy_list"),
                     reverse("accounts:detail", args=[self.account.pk]),
                     f"/accounting/books/{b}/accounts/",
                     f"/accounting/books/{b}/payments/",
                     f"/accounting/books/{b}/reports/",
                     f"/accounting/books/{b}/",
                     "/crm/contact/list/",
                     "/crm/company/list/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_warehouses_purchases_and_the_catalog_stay_open(self):
        self.operations()
        b = self.book.pk
        for path in ("/operating/warehouses/",
                     f"/accounting/books/{b}/purchases/",
                     f"/accounting/books/{b}/purchases/new/",
                     reverse("accounts:legacy_purchase_order_list"),
                     "/crm/customer_autocomplete/?customer=zi",
                     "/marketing/product_list/"):
            with self.subTest(path=path):
                self.assertNotEqual(self.client.get(path).status_code, 403)

    def test_the_menu_and_the_top_bar_follow(self):
        self.operations()
        page = self.client.get("/operating/warehouses/").content.decode()
        self.assertNotIn('id="topBarAccountsBtn"', page)
        self.assertNotIn('href="%s"' % reverse("accounts:legacy_list"), page)
        self.assertNotIn('href="/crm/contact/list/"', page)
        self.assertIn('href="/operating/warehouses/"', page)

    def test_search_returns_no_customer(self):
        from crm.models import Company
        Company.objects.create(name="Zircon Buyer Ltd")
        self.operations()
        results = self.client.get("/search/?q=Zircon&type=all").json()["results"]
        self.assertFalse([r for r in results if is_accounts_path(r.get("url") or "")])

    def suppliers_and_customers(self):
        from crm.models import Company
        from operating.models import Warehouse
        # The receipt lists its accounts once the book has somewhere to receive into.
        Warehouse.objects.create(name="Ergene Factory", accounting_book=self.book)
        mill = Company.objects.create(name="Zircon Mill")
        buyer = Company.objects.create(name="Zircon Buyer")
        CurrentAccount.objects.create(book=self.book, code="S-MILL", name="Zircon Mill",
                                      type="supplier", company=mill, default_currency=self.usd)
        CurrentAccount.objects.create(book=self.book, code="C-BUYER", name="Zircon Buyer",
                                      type="customer", company=buyer, default_currency=self.usd)

    def test_operations_find_suppliers_only(self):
        self.suppliers_and_customers()
        self.operations()
        found = self.client.get("/crm/customer_autocomplete/?customer=zircon").content.decode()
        self.assertIn("Zircon Mill", found)
        self.assertNotIn("Zircon Buyer", found)
        nothing = self.client.get("/crm/customer_autocomplete/?customer=nobody").content.decode()
        self.assertNotIn("customer-ac-create", nothing)

        receipt = self.client.get(f"/accounting/books/{self.book.pk}/purchases/new/")
        self.assertEqual(receipt.status_code, 200)
        self.assertContains(receipt, "Zircon Mill")
        self.assertNotContains(receipt, "Zircon Buyer")

    def test_a_role_with_it_still_finds_everyone(self):
        self.suppliers_and_customers()
        self.sign_in("orders", "beyond_sales", "accounts_customers", "prices_customers")
        found = self.client.get("/crm/customer_autocomplete/?customer=zircon").content.decode()
        self.assertIn("Zircon Mill", found)
        self.assertIn("Zircon Buyer", found)
        receipt = self.client.get(f"/accounting/books/{self.book.pk}/purchases/new/")
        self.assertContains(receipt, "Zircon Buyer")

    def test_a_role_with_it_sees_everything_as_before(self):
        user = self.sign_in("orders", "beyond_sales", "accounts_customers", "prices_customers")
        self.assertTrue(sees_accounts(user))
        self.assertEqual(self.client.get(f"/accounting/books/{self.book.pk}/accounts/").status_code, 200)
        page = self.client.get("/operating/warehouses/").content.decode()
        self.assertIn('id="topBarAccountsBtn"', page)

    def test_order_search_answers_with_the_viewers_books_only(self):
        Order.objects.create(order_number="ORD-2026-000901", current_account=self.account)
        Order.objects.create(order_number="ORD-2026-000902",
                             current_account=self.account_in(self.other))
        Order.objects.create(order_number="ORD-2026-000903")  # no book yet
        self.sign_in("orders", "beyond_sales", "accounts_customers", "prices_customers")
        names = [r["name"] for r in
                 self.client.get("/search/?q=ORD-2026-0009&type=orders").json()["results"]]
        self.assertEqual(names, ["ORD-2026-000901"])

        boss = User.objects.create_superuser("boss_search", "b@x.test", "pw")
        self.client.force_login(boss)
        names = {r["name"] for r in
                 self.client.get("/search/?q=ORD-2026-0009&type=orders").json()["results"]}
        self.assertEqual(names, {"ORD-2026-000901", "ORD-2026-000902", "ORD-2026-000903"})
