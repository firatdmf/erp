"""Order editing is a PAGE, not a drawer.

The edit form used to open in a 50vw sidebar over the order detail, and
the overlay closed on any click that landed outside the panel — one
stray click and everything typed was gone. It is now a page of its own,
which has no outside to click.

The AJAX branch still returns the bare partial: the CREATE sidebar
loads the same form, so that path has to keep working.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from marketing.models import Product
from .models import Order, OrderItem


class OrderEditIsAFullPage(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        # The order needs its cari: an order page is refused unless the
        # viewer is assigned the book the row belongs to, and an Order
        # reaches its book through cari.book.
        book = Book.objects.create(name="Laleli Fabric")
        cari = CariAccount.objects.create(
            book=book, code="C-284", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(order_number="DK0000284", cari=cari)
        product = Product.objects.create(title="Crepe", sku="KZL000315", price=10)
        OrderItem.objects.create(order=self.order, product=product,
                                 quantity=Decimal("156.00"), price=Decimal("2.50"))
        self.client.force_login(
            User.objects.create_superuser("editor", "e@t.com", "pw"))
        self.url = reverse("operating:edit_order", kwargs={"pk": self.order.pk})

    def test_it_renders_a_whole_page(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "operating/edit_order_page.html")

    def test_the_page_carries_the_form_the_sidebar_used(self):
        """The page wraps the SAME partial rather than reviving the old
        edit_order.html, so create and edit stay one form."""
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "operating/partials/create_order_form.html")
        self.assertTemplateNotUsed(resp, "operating/edit_order.html")

    def test_it_offers_the_way_back_to_the_order(self):
        resp = self.client.get(self.url)
        self.assertContains(
            resp, reverse("operating:order_detail", kwargs={"pk": self.order.pk}))

    def test_the_ajax_branch_still_returns_the_bare_partial(self):
        """The create sidebar loads this same endpoint; giving it a full
        page would nest a whole <html> document inside the drawer."""
        resp = self.client.get(self.url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "operating/partials/create_order_form.html")
        self.assertTemplateNotUsed(resp, "operating/edit_order_page.html")

    def test_the_order_detail_links_to_the_page_instead_of_opening_a_drawer(self):
        resp = self.client.get(
            reverse("operating:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # base.html still DEFINES the drawer opener (it is shared markup);
        # what must be gone is any button wired to call it.
        self.assertNotIn('onclick="openEditOrderSidebar', body)
        self.assertIn(self.url, body)


class SavingAnEditLandsOnTheOrder(TestCase):
    """Saving used to leave you sitting on the form you had just saved.

    The form posts over XHR, and OrderEdit answers that with 200 JSON
    carrying redirect_url rather than a 302. The page only looked for
    `order_id`, so it fell through to a plain reload — of the edit page.
    """

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        book = Book.objects.create(name="Laleli Fabric")
        cari = CariAccount.objects.create(
            book=book, code="C-294", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(order_number="DK0000294", cari=cari)
        product = Product.objects.create(title="Crepe", sku="KZL000316", price=10)
        OrderItem.objects.create(order=self.order, product=product,
                                 quantity=Decimal("10.00"), price=Decimal("2.50"))
        self.client.force_login(User.objects.create_superuser("ed2", "e2@t.com", "pw"))
        self.url = reverse("operating:edit_order", kwargs={"pk": self.order.pk})

    def test_an_xhr_save_names_the_order_page_to_go_to(self):
        resp = self.client.post(self.url, {"order_number": self.order.order_number},
                                headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["redirect_url"],
                         reverse("operating:order_detail", kwargs={"pk": self.order.pk}))

    def test_the_form_follows_that_redirect_instead_of_reloading(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn("data.redirect_url", html)
        self.assertIn("window.location.href = data.redirect_url", html)


class AnOrderCanBeEmptied(TestCase):
    """Every line can be deleted and the order still saved.

    The form used to refuse with "Add at least one product". Both views
    skip item processing when the payload is empty, so an emptied order
    was always a saveable state — the block was the form protecting the
    server from something it handles fine.
    """

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        book = Book.objects.create(name="Laleli Fabric")
        cari = CariAccount.objects.create(
            book=book, code="C-295", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(order_number="DK0000295", cari=cari)
        product = Product.objects.create(title="Crepe", sku="KZL000317", price=10)
        self.item = OrderItem.objects.create(
            order=self.order, product=product,
            quantity=Decimal("12.00"), price=Decimal("2.50"))
        self.client.force_login(User.objects.create_superuser("ed3", "e3@t.com", "pw"))
        self.url = reverse("operating:edit_order", kwargs={"pk": self.order.pk})

    def test_deleting_every_line_saves(self):
        import json
        resp = self.client.post(
            self.url,
            {"order_number": self.order.order_number,
             "deleted_items": json.dumps([self.item.pk]),
             "product_json_input": ""},
            headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertEqual(self.order.items.count(), 0)

    def test_the_form_no_longer_blocks_an_empty_order(self):
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("Add at least one product", html)
