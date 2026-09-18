"""Only an admin may delete a warehouse — the button and the endpoint both.

Admin is a superuser/staff user or a member holding the "admin"
permission (views_warehouse._is_admin). Everyone else may edit.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.models import Permission
from operating.models import Warehouse


class OnlyAdminDeletesAWarehouse(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Laleli Fabric")
        self.warehouse = Warehouse.objects.create(name="Laleli", accounting_book=self.book)
        User = get_user_model()
        self.staffer = User.objects.create_user("staffer", password="pw")
        self.staffer.member.books.add(self.book)
        self.admin = User.objects.create_user("boss", password="pw")
        self.admin.member.books.add(self.book)
        self.admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])

    def _delete(self, user):
        self.client.force_login(user)
        return self.client.post(reverse("operating:warehouse_delete", args=[self.warehouse.pk]))

    def _detail(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("operating:warehouse_detail", args=[self.warehouse.pk])).content.decode()

    def test_a_non_admin_cannot_delete_it(self):
        self._delete(self.staffer)
        self.assertTrue(Warehouse.objects.filter(pk=self.warehouse.pk).exists())

    def test_a_non_admin_is_not_offered_the_button(self):
        self.assertNotIn("openDeleteConfirm()\"", self._detail(self.staffer))

    def test_an_admin_can_delete_it(self):
        self.assertIn("openDeleteConfirm()\"", self._detail(self.admin))
        self._delete(self.admin)
        self.assertFalse(Warehouse.objects.filter(pk=self.warehouse.pk).exists())
