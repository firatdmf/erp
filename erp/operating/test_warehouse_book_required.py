"""A warehouse must state which book owns its stock.

The link was optional, and a warehouse that answered "no book" was shown
to every member and searchable from every order. Who may read a shelf,
which orders may draw on it and whose net worth it counts toward all
follow from this field, so it is not something a warehouse may leave
blank.
"""
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book

from .models import Warehouse


class WarehouseNeedsABook(TestCase):
    def setUp(self):
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        User = get_user_model()
        self.outsider = User.objects.create_user("ergene_only", password="pw")
        self.outsider.member.books.add(self.ergene)
        self.outsider.member.default_book = self.ergene
        self.outsider.member.save()
        self.client.force_login(self.outsider)

    def test_the_database_refuses_a_bookless_warehouse(self):
        with self.assertRaises(IntegrityError):
            Warehouse.objects.create(name="Kayip Depo")

    def _create(self, **extra):
        data = {"name": "Yeni Depo", "location": "", "description": ""}
        data.update(extra)
        return self.client.post(reverse("operating:create_warehouse"), data)

    def test_the_form_refuses_to_create_one_without_a_book(self):
        self._create()
        self.assertFalse(Warehouse.objects.filter(name="Yeni Depo").exists())

    def test_the_form_creates_it_when_a_book_is_named(self):
        self._create(accounting_book=str(self.ergene.pk))
        wh = Warehouse.objects.get(name="Yeni Depo")
        self.assertEqual(wh.accounting_book, self.ergene)

    def test_a_book_the_member_does_not_work_in_is_refused(self):
        """The id comes from a form the browser controls, so it is
        checked against the member's assignments rather than trusted."""
        self._create(accounting_book=str(self.laleli.pk))
        self.assertFalse(Warehouse.objects.filter(name="Yeni Depo").exists())

    def test_the_dropdown_offers_only_their_own_books(self):
        html = self.client.get(reverse("operating:create_warehouse")).content.decode()
        # The combined-warehouse hint mentions a fictional "Laleli Store".
        html = html.replace("Laleli Store + Factory Solids", "")
        self.assertIn("Ergene Fabric", html)
        self.assertNotIn("Laleli Fabric", html)

    def test_a_book_holding_stock_cannot_be_deleted(self):
        """PROTECT, not SET_NULL — there is no null to fall back to, and
        a book must not be deleted out from under its warehouses."""
        from django.db.models import ProtectedError
        Warehouse.objects.create(name="Ergene Depo", accounting_book=self.ergene)
        with self.assertRaises(ProtectedError):
            self.ergene.delete()
