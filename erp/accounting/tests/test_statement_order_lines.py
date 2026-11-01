"""An account statement's order rows open to the order's lines.

On the page a chevron fetches them (accounts:statement_order_lines); the
printed statement — the PDF the page's Print opens, the same one the CRM
pages print — carries them under each sale. The row names the order once,
by its number, linked: it used to say "Order #314" beside ORD-2026-000016.

Run with:
    python manage.py test accounting.tests.test_statement_order_lines
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderAdjustment, OrderItem


class StatementOrderLines(TestCase):

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.emin = Contact.objects.create(name="Emin Kosta")
        self.account = CurrentAccount.objects.create(
            book=self.laleli, code="ACC-095", name="Emin Kosta",
            contact=self.emin, default_currency=self.usd)
        crepe = Product.objects.create(title="Crepe", sku="KZL000315", price=10)
        black = ProductVariant.objects.create(product=crepe, variant_sku="KZL000315.BLACK")
        self.order = Order.objects.create(order_number="ORD-2026-000016",
                                          current_account=self.account, contact=self.emin)
        OrderItem.objects.create(order=self.order, product=crepe, product_variant=black,
                                 quantity=Decimal("156.00"), price=Decimal("2.50"))
        OrderAdjustment.objects.create(order=self.order, label="Delivery", amount=Decimal("25.00"))
        self.sale = CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.laleli, date="2026-09-24",
            amount=Decimal("415.00"), currency=self.usd, movement_type="order_sale",
            source_type=ContentType.objects.get_for_model(Order), source_id=self.order.pk,
            description=f"Order #{self.order.pk}", reference="ORD-2026-000016")
        self.user = get_user_model().objects.create_superuser("ledger", "l@x.com", "pw")
        self.client.force_login(self.user)

    def _page(self):
        return self.client.get(reverse("accounts:statement", args=[self.account.pk]))

    def test_the_order_row_has_a_chevron_for_its_lines(self):
        url = reverse("accounts:statement_order_lines", args=[self.account.pk, self.order.pk])
        resp = self._page()
        self.assertContains(resp, 'class="st-chev"')
        self.assertContains(resp, f'data-lines-url="{url}"')

    def test_the_order_is_named_once_by_its_number(self):
        resp = self._page()
        self.assertContains(resp, reverse("operating:order_detail", args=[self.order.pk]))
        self.assertContains(resp, "ORD-2026-000016")
        self.assertNotContains(resp, f"Order #{self.order.pk}")

    def test_the_page_is_called_account_statement(self):
        self.assertContains(self._page(), "Account Statement — Emin Kosta")

    def test_print_opens_the_statement_pdf(self):
        resp = self._page()
        self.assertContains(
            resp, f'href="{reverse("accounts:statement_print_combined")}?ids={self.account.pk}"')
        self.assertNotContains(resp, "window.print();")

    def test_the_chevron_fetches_the_lines(self):
        resp = self.client.get(
            reverse("accounts:statement_order_lines", args=[self.account.pk, self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Crepe")
        self.assertContains(resp, "KZL000315.BLACK")
        self.assertContains(resp, "$390.00")
        self.assertContains(resp, "Delivery")
        self.assertContains(resp, "$415.00")

    def test_an_order_billed_elsewhere_is_not_read_through_this_account(self):
        other = CurrentAccount.objects.create(
            book=self.laleli, code="ACC-096", name="Someone else", default_currency=self.usd)
        resp = self.client.get(
            reverse("accounts:statement_order_lines", args=[other.pk, self.order.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_the_printed_statement_carries_the_lines_and_the_chip(self):
        resp = self.client.get(reverse("accounts:statement_print_combined"),
                               {"ids": str(self.account.pk), "html": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'class="kind">STATEMENT<')
        self.assertContains(resp, "ACC-095")
        self.assertContains(resp, "KZL000315.BLACK")
        self.assertContains(resp, 'class="lines"')
        self.assertContains(resp, "Delivery")
        self.assertContains(resp, "Balance due")
        self.assertNotContains(resp, f"Order #{self.order.pk}")

    def test_the_printed_statement_is_signed_like_the_order_sheet(self):
        resp = self.client.get(reverse("accounts:statement_print_combined"),
                               {"ids": str(self.account.pk), "html": "1"})
        self.assertContains(resp, 'class="nejum"')
        self.assertContains(resp, "Nejum")
