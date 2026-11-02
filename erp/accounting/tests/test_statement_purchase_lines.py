"""An account statement's purchase rows open to the lines bought, the way
its order rows open to the lines sold.

On the page a chevron fetches them (accounts:statement_purchase_lines);
the printed statement carries them under the purchase.

Run with:
    python manage.py test accounting.tests.test_statement_purchase_lines
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, InvoiceItem
from crm.models import Company
from marketing.models import Product, ProductVariant


class StatementPurchaseLines(TestCase):

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="ACC-201", name="Topallar", default_currency=self.usd,
            company=Company.objects.create(name="Topallar"))
        crepe = Product.objects.create(title="Crepe", sku="KZL000315", price=10)
        black = ProductVariant.objects.create(product=crepe, variant_sku="KZL000315.BLACK")
        self.purchase = Invoice.objects.create(
            book=self.book, current_account=self.supplier, type="purchase",
            series="PUR", number="PUR-2026-000501", status="ordered",
            date=date(2026, 9, 1), due_date=date(2026, 10, 1), currency=self.usd)
        InvoiceItem.objects.create(invoice=self.purchase, line_no=1, product=crepe, variant=black,
                                   description="Crepe black", quantity=Decimal("120.00"),
                                   unit="m", unit_price=Decimal("1.10"), tax_rate=0)
        # A line typed by hand, tied to nothing in the catalogue.
        InvoiceItem.objects.create(invoice=self.purchase, line_no=2,
                                   description="Dyeing, lot 7", quantity=Decimal("1"),
                                   unit="piece", unit_price=Decimal("40.00"), tax_rate=0)
        self.purchase.receive()
        self.user = get_user_model().objects.create_superuser("ledger", "l@x.com", "pw")
        self.client.force_login(self.user)

    def _lines_url(self, account=None):
        return reverse("accounts:statement_purchase_lines",
                       args=[(account or self.supplier).pk, self.purchase.pk])

    def test_the_purchase_row_has_a_chevron_for_its_lines(self):
        resp = self.client.get(reverse("accounts:statement", args=[self.supplier.pk]))
        self.assertContains(resp, f'data-lines-url="{self._lines_url()}"')

    def test_the_chevron_fetches_the_lines(self):
        resp = self.client.get(self._lines_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Crepe")
        self.assertContains(resp, "KZL000315.BLACK")
        self.assertContains(resp, "$132.00")
        self.assertContains(resp, "Dyeing, lot 7")
        self.assertContains(resp, "$172.00")
        self.assertContains(resp, reverse("accounts:purchase_order_detail", args=[self.purchase.pk]))

    def test_a_purchase_on_another_account_is_not_read_through_this_one(self):
        other = CurrentAccount.objects.create(
            book=self.book, code="ACC-202", name="Someone else", default_currency=self.usd)
        self.assertEqual(self.client.get(self._lines_url(other)).status_code, 404)

    def test_the_printed_statement_carries_the_lines(self):
        resp = self.client.get(reverse("accounts:statement_print_combined"),
                               {"ids": str(self.supplier.pk), "html": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'class="lines"')
        self.assertContains(resp, "KZL000315.BLACK")
        self.assertContains(resp, "Dyeing, lot 7")
        self.assertContains(resp, "$132.00")
