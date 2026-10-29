"""Production, in beta: reached from the Operating menu, not from an
order's documents. The menu's page lists one book's open orders, each
opening its production sheet."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from erp.nav import NAV_SECTIONS
from operating.models import Order


class ProductionBeta(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.accounts = {
            book.pk: CurrentAccount.objects.create(
                book=book, code=f"C-{book.pk}", name="Karven", type="customer",
                default_currency=usd)
            for book in (self.laleli, self.ergene)}
        self.open = self._order(self.laleli, "DK-OPEN", "pending")
        self.packing = self._order(self.laleli, "DK-PACKING", "packaging")
        self.shipped = self._order(self.laleli, "DK-SHIPPED", "shipped")
        self.other_book = self._order(self.ergene, "DK-ERGENE", "pending")
        self.client.force_login(
            get_user_model().objects.create_superuser("boss", "b@t.com", "pw"))

    def _order(self, book, number, status):
        return Order.objects.create(order_number=number, order_status=status,
                                    current_account=self.accounts[book.pk])

    def test_the_list_holds_the_books_open_orders(self):
        r = self.client.get(reverse("operating:production_orders_scoped",
                                    kwargs={"book_id": self.laleli.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual({o.pk for o in r.context["orders"]},
                         {self.open.pk, self.packing.pk})
        self.assertContains(r, reverse("operating:order_production", args=[self.open.pk]))

    def test_the_menu_link_lands_on_a_book(self):
        r = self.client.get(reverse("operating:production_orders"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/production/", r["Location"])

    def test_the_operating_menu_carries_it_as_beta(self):
        operating = next(s for s in NAV_SECTIONS if s["key"] == "operations")
        urls = [i.get("url") for g in operating["groups"] for i in g["items"]]
        self.assertIn("operating:production_orders", urls)

    def test_the_order_page_no_longer_offers_it(self):
        r = self.client.get(reverse("operating:order_detail", args=[self.open.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, reverse("operating:order_production", args=[self.open.pk]))
