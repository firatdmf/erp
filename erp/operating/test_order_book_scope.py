"""The orders list shows one book's orders.

/operating/orders/ listed every book's sales at once, so Ergene's page
showed Laleli's customers. An Order carries no book of its own — the
link is its cari, which is where the sale posts — so the list filters on
cari__book.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount

from .models import Order
from .views import OrderList


class OrderListIsPerBook(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        self.laleli_order = self._order(self.laleli, "Karven")
        self.ergene_order = self._order(self.ergene, "Bursa Tekstil")
        # No customer at all — the shape order 237 is in: cancelled, and
        # never resolved to a cari.
        self.homeless = Order.objects.create(order_number="DK-NOCARI")

        User = get_user_model()
        self.boss = User.objects.create_superuser("boss", "b@t.com", "pw")
        self.ergene_only = User.objects.create_user("ergene_only", password="pw")
        self.ergene_only.member.books.add(self.ergene)
        self.ergene_only.member.default_book = self.ergene
        self.ergene_only.member.save()

    def _order(self, book, supplier):
        cari = CariAccount.objects.create(
            book=book, code=f"C-{book.pk}", name=supplier, type="customer",
            default_currency=self.usd)
        return Order.objects.create(order_number=f"DK-{book.pk}", cari=cari)

    def _ids(self, book, user=None):
        from django.test import RequestFactory
        req = RequestFactory().get("/x")
        req.user = user or self.boss
        req.book = book
        v = OrderList()
        v.setup(req)
        v.request = req
        return set(v.get_queryset().values_list("id", flat=True))

    def test_a_book_sees_its_own_orders(self):
        self.assertIn(self.laleli_order.pk, self._ids(self.laleli))
        self.assertIn(self.ergene_order.pk, self._ids(self.ergene))

    def test_a_book_does_not_see_another_books_orders(self):
        self.assertNotIn(self.ergene_order.pk, self._ids(self.laleli))
        self.assertNotIn(self.laleli_order.pk, self._ids(self.ergene))

    def test_the_books_never_show_the_same_order_twice(self):
        self.assertEqual(self._ids(self.laleli) & self._ids(self.ergene), set())

    def test_an_order_with_no_cari_is_in_no_book(self):
        """There should never BE one — the only one that existed (order
        237: empty, cancelled, no customer) was deleted rather than
        given a home. Pinning such an order to a fallback book was tried
        and dropped: quietly filing an order that violates the invariant
        under some plausible book hides the violation instead of showing
        it. If one appears, it is meant to be conspicuous."""
        self.assertNotIn(self.homeless.pk, self._ids(self.laleli))
        self.assertNotIn(self.homeless.pk, self._ids(self.ergene))

    def test_the_old_unscoped_url_redirects_to_the_working_book(self):
        self.client.force_login(self.ergene_only)
        resp = self.client.get(reverse("operating:order_list"))
        self.assertRedirects(
            resp,
            reverse("operating:order_list_scoped", kwargs={"book_id": self.ergene.pk}),
            fetch_redirect_response=False)

    def test_the_redirect_keeps_the_query_string(self):
        self.client.force_login(self.ergene_only)
        resp = self.client.get(reverse("operating:order_list") + "?status=pending")
        self.assertTrue(resp["Location"].endswith("?status=pending"))

    def test_a_book_the_member_is_not_assigned_is_not_reachable(self):
        """404 rather than 403 — whether a book exists is not something an
        unassigned member should learn from the status code."""
        self.client.force_login(self.ergene_only)
        resp = self.client.get(
            reverse("operating:order_list_scoped", kwargs={"book_id": self.laleli.pk}))
        self.assertEqual(resp.status_code, 404)
