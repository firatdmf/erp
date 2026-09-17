"""An invoice is a printout of an order or a purchase, and nothing more.

"Get invoice" on either lays the record out as an invoice, for printing
and as an Excel download. It is built from the record every time, so it
stores nothing, posts nothing, and follows every edit — completing an
order no longer cuts an invoice row, and renaming a variant shows up on
the next printout without anything having to be rewritten.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.invoice_doc import build_order_doc, build_purchase_doc
from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, InvoiceItem
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem
from operating.views_warehouse import apply_order_status_change


class InvoiceDocBase(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", brand_name="Karven Home Collection")
        self.customer = CurrentAccount.objects.create(
            book=self.book, code="C-501", name="Oleg Textiles", type="customer",
            default_currency=self.usd, billing_city="Moscow")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-501", name="Bursa Mill", type="supplier",
            default_currency=self.usd)
        self.product = Product.objects.create(title="Velvet Moss", sku="KZL000501", price=10)
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="KZL000501.G1")

        self.order = Order.objects.create(order_number="DK0000501",
                                          current_account=self.customer,
                                          order_status="pending")
        OrderItem.objects.create(order=self.order, product=self.product,
                                 product_variant=self.variant,
                                 quantity=Decimal("40.00"), price=Decimal("3.25"))
        OrderItem.objects.create(order=self.order, product=self.product,
                                 quantity=Decimal("0"), price=Decimal("9.00"))

        self.purchase = Invoice.objects.create(
            book=self.book, current_account=self.supplier, type="purchase",
            series="PUR", number="PUR-2026-000501", status="issued",
            date=date(2026, 9, 1), due_date=date(2026, 10, 1), currency=self.usd)
        InvoiceItem.objects.create(invoice=self.purchase, line_no=1, product=self.product,
                                   description="Velvet Moss greige", quantity=Decimal("120.00"),
                                   unit="mt", unit_price=Decimal("1.10"), tax_rate=0)

        self.user = User.objects.create_user("staff_invoice", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.client.force_login(self.user)


class TheOrderInvoice(InvoiceDocBase):

    def test_it_mirrors_the_order(self):
        doc = build_order_doc(self.order)
        self.assertEqual(doc.kind, "sales")
        self.assertEqual(doc.number, "DK0000501")
        self.assertEqual(doc.party.name, "Oleg Textiles")
        self.assertEqual(doc.issuer.name, "Karven Home Collection")
        # The zero-quantity line bills nothing, so it is not on the invoice.
        self.assertEqual(len(doc.lines), 1)
        self.assertEqual(doc.lines[0].sku, "KZL000501.G1")
        self.assertEqual(doc.total, Decimal("130.00"))

    def test_the_page_prints_it(self):
        resp = self.client.get(reverse("operating:order_invoice", args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "DK0000501")
        self.assertContains(resp, "Oleg Textiles")
        self.assertContains(resp, "KZL000501.G1")
        self.assertContains(resp, "130.00")

    def test_the_page_is_print_only(self):
        body = self.client.get(
            reverse("operating:order_invoice", args=[self.order.pk])).content.decode()
        # A bare document that opens the print dialog — no app layout, no
        # toolbar, no language picker.
        self.assertIn("window.print()", body)
        self.assertNotIn("global-top-bar", body)
        self.assertNotIn("Download Excel", body)
        self.assertNotIn("Invoice Settings", body)

    def test_it_prints_in_the_apps_language(self):
        from django.conf import settings as dj_settings
        self.client.cookies[dj_settings.LANGUAGE_COOKIE_NAME] = "tr"
        resp = self.client.get(reverse("operating:order_invoice", args=[self.order.pk]))
        self.assertContains(resp, "<title>Fatura DK0000501</title>", html=False)

    def test_the_excel_download_carries_the_same_figures(self):
        import openpyxl
        resp = self.client.get(reverse("operating:order_invoice_excel", args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('filename="invoice-DK0000501.xlsx"', resp["Content-Disposition"])
        wb = openpyxl.load_workbook(BytesIO(resp.content))
        values = [c.value for row in wb.active.iter_rows() for c in row if c.value is not None]
        self.assertIn("No: DK0000501", values)
        self.assertIn("Oleg Textiles", values)
        self.assertIn(130.0, values)

    def test_it_follows_an_edit(self):
        item = self.order.items.get(product_variant=self.variant)
        item.price = Decimal("4.00")
        item.save()
        self.assertEqual(build_order_doc(self.order).total, Decimal("160.00"))

    def test_it_follows_a_variant_rename(self):
        self.variant.variant_sku = "K24861T.G77"
        self.variant.save()
        self.order.refresh_from_db()
        self.assertEqual(build_order_doc(self.order).lines[0].sku, "K24861T.G77")

    def test_the_order_page_offers_it(self):
        resp = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertContains(resp, reverse("operating:order_invoice", args=[self.order.pk]))
        self.assertContains(resp, reverse("operating:order_invoice_excel", args=[self.order.pk]))
        self.assertContains(resp, "Get invoice")
        self.assertNotContains(resp, "Create invoice")

    def test_completing_the_order_stores_no_invoice(self):
        self.assertEqual(apply_order_status_change(self.order, "shipped", user=self.user),
                         (True, None))
        self.assertFalse(Invoice.objects.filter(order=self.order).exists())
        # The receivable is the order's own movement, as before.
        self.assertTrue(self.customer.movements.filter(movement_type="order_sale").exists())

    def test_another_books_order_is_refused(self):
        other = Book.objects.create(name="Ergene Fabric")
        self.customer.book = other
        self.customer.save()
        for name in ("operating:order_invoice", "operating:order_invoice_excel"):
            with self.subTest(url=name):
                self.assertEqual(
                    self.client.get(reverse(name, args=[self.order.pk])).status_code, 404)


class ThePurchaseInvoice(InvoiceDocBase):

    def test_it_mirrors_the_purchase(self):
        doc = build_purchase_doc(self.purchase)
        self.assertEqual(doc.kind, "purchase")
        self.assertEqual(doc.number, "PUR-2026-000501")
        self.assertEqual(doc.party.name, "Bursa Mill")
        self.assertEqual(doc.total, Decimal("132.00"))

    def test_the_page_and_the_download(self):
        resp = self.client.get(reverse("accounts:purchase_invoice", args=[self.purchase.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PURCHASE INVOICE")
        self.assertContains(resp, "Bursa Mill")
        self.assertContains(resp, "132.00")
        resp = self.client.get(reverse("accounts:purchase_invoice_excel", args=[self.purchase.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(".xlsx", resp["Content-Disposition"])

    def test_the_purchase_page_offers_it(self):
        resp = self.client.get(reverse("accounts:purchase_order_detail", args=[self.purchase.pk]))
        self.assertContains(resp, reverse("accounts:purchase_invoice", args=[self.purchase.pk]))
        self.assertContains(resp, reverse("accounts:purchase_invoice_excel", args=[self.purchase.pk]))
        self.assertNotContains(resp, "View invoice")

    def test_a_sales_record_is_not_a_purchase(self):
        sale = Invoice.objects.create(
            book=self.book, current_account=self.customer, type="sales", number="INV-9",
            date=date(2026, 9, 1), due_date=date(2026, 10, 1), currency=self.usd)
        resp = self.client.get(reverse("accounts:purchase_invoice", args=[sale.pk]))
        self.assertEqual(resp.status_code, 404)


class TheOldInvoicePage(InvoiceDocBase):
    """Bookmarks and ledger rows still point at /accounts/invoices/<id>/."""

    def test_a_purchase_goes_to_its_purchase(self):
        resp = self.client.get(reverse("accounts:invoice_detail", args=[self.purchase.pk]))
        self.assertRedirects(resp, reverse("accounts:purchase_order_detail", args=[self.purchase.pk]),
                             fetch_redirect_response=False)

    def test_an_order_invoice_goes_to_the_orders_invoice(self):
        old = Invoice.objects.create(
            book=self.book, current_account=self.customer, type="sales", number="INV-1",
            date=date(2026, 9, 1), due_date=date(2026, 10, 1), currency=self.usd,
            order=self.order)
        resp = self.client.get(reverse("accounts:invoice_detail", args=[old.pk]))
        self.assertRedirects(resp, reverse("operating:order_invoice", args=[self.order.pk]),
                             fetch_redirect_response=False)
