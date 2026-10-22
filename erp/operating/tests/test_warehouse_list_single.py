"""One warehouse in reach: the warehouses link opens it directly.

A list of one is a click with no choice in it. Admins still get the list,
since the "new warehouse" button lives there.

Run with:
    python manage.py test operating.tests.test_warehouse_list_single
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory

from operating.models import Warehouse


class OneWarehouseOpensDirectly(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        # Another book's warehouse — out of reach, so it must not count.
        other = Book.objects.create(name="Laleli", base_currency=usd)
        Warehouse.objects.create(name="Laleli Depo", accounting_book=other)

        self.user = get_user_model().objects.create_user("wh", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.client.force_login(self.user)

    def test_list_redirects_to_the_one_warehouse(self):
        resp = self.client.get(reverse("operating:warehouse_list"))
        self.assertRedirects(
            resp, reverse("operating:warehouse_detail", args=[self.wh.pk]))

    def test_detail_has_no_back_link_to_the_list(self):
        resp = self.client.get(
            reverse("operating:warehouse_detail", args=[self.wh.pk]))
        self.assertNotContains(resp, "Back to warehouses")

    def test_two_warehouses_keep_the_list(self):
        Warehouse.objects.create(name="Ergene Depo", accounting_book=self.book)
        resp = self.client.get(reverse("operating:warehouse_list"))
        self.assertEqual(resp.status_code, 200)
        detail = self.client.get(
            reverse("operating:warehouse_detail", args=[self.wh.pk]))
        self.assertContains(detail, "Back to warehouses")

    def test_admin_keeps_the_list(self):
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get(reverse("operating:warehouse_list"))
        self.assertEqual(resp.status_code, 200)
