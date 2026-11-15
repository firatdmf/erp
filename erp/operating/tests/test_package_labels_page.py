"""The Package labels page: packages still to go out, a label a click away,
for whoever prints labels — the operations manager included, who never
opens an order.

Run with:
    python manage.py test operating.tests.test_package_labels_page
"""
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from operating.models import Order, Pack

CDN = "https://cdn.test/qr.png"


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class PackageLabelsPage(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
    def setUp(self, _upload):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.open = self.order_in(self.ergene, "ORD-2026-000701", "packaging")
        self.shipped = self.order_in(self.ergene, "ORD-2026-000702", "shipped")
        self.elsewhere = self.order_in(self.laleli, "ORD-2026-000703", "packaging")
        self.pack = Pack.objects.get(order=self.open)

    def order_in(self, book, number, status):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{uuid4().hex[:8]}", name="Karven",
            type="customer", default_currency=self.usd)
        order = Order.objects.create(order_number=number, order_status=status,
                                     current_account=account)
        Pack.objects.create(order=order, pack_number=1)
        return order

    def sign_in(self, name, *grants):
        user = User.objects.create_user(name, password="pw")
        user.member.books.add(self.ergene)
        for grant in grants:
            user.member.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        self.client.force_login(user)
        return user

    def test_the_operations_manager_prints_package_labels_without_orders(self, _upload):
        # The Operations role: Print labels, and the No orders restriction.
        self.sign_in("mustafa", "print_labels", "beyond_sales", "manager")
        page = self.client.get(reverse("operating:package_labels"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "ORD-2026-000701")
        self.assertNotContains(page, "ORD-2026-000702")  # already gone
        self.assertNotContains(page, "ORD-2026-000703")  # another book's
        self.assertContains(page, reverse("operating:pack_label", args=[self.pack.pk]))
        self.assertContains(page, reverse("operating:order_pack_labels", args=[self.open.pk]))

        with patch("operating.pack_label.labels_pdf_bytes", return_value=b"%PDF"):
            self.assertEqual(self.client.get(
                reverse("operating:pack_label", args=[self.pack.pk])).status_code, 200)
            self.assertEqual(self.client.get(
                reverse("operating:order_pack_labels", args=[self.open.pk])).status_code, 200)
        # The order itself stays closed to him.
        self.assertEqual(self.client.get(
            reverse("operating:order_detail", args=[self.open.pk])).status_code, 403)

    def test_the_menu_offers_it_to_label_printers_only(self, _upload):
        self.sign_in("mustafa", "print_labels", "beyond_sales", "manager")
        home = self.client.get(reverse("operating:warehouse_list"))
        self.assertContains(home, reverse("operating:package_labels"))

        self.sign_in("zeynep", "beyond_sales", "orders")
        self.assertEqual(self.client.get(reverse("operating:package_labels")).status_code, 403)
        home = self.client.get(reverse("operating:warehouse_list"))
        self.assertNotContains(home, reverse("operating:package_labels"))
