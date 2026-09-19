# to run this test, use the command:
# python manage.py test accounting.tests.test_purchase_line_spec

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, InvoiceItem
from marketing.models import (
    Product, ProductVariant, ProductVariantAttribute, ProductVariantAttributeValue,
)


class PurchaseLineSpecTest(TestCase):
    """A purchased line names what was bought, one fact to a row.

    The receiver checks the goods against the line, so the SKU stands on
    its own and every attribute appears under its own name: "colour:
    ecru", not a run-on string in which nobody can tell which value
    belongs to which attribute.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.user = get_user_model().objects.create_superuser(
            username="spec_buyer", password="pw", email="s@a.c")
        self.client.force_login(self.user)

        product = Product.objects.create(title="Baklava")
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="S-BAKLAVA.R1106ECRU-305")
        for name, value in (("width", "305"), ("color", "r-1106-ecru")):
            attribute = ProductVariantAttribute.objects.create(name=name)
            self.variant.product_variant_attribute_values.add(
                ProductVariantAttributeValue.objects.create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=value,
                )
            )

        self.invoice = Invoice.objects.create(
            book=self.book, current_account=self.supplier, currency=self.usd,
            type="purchase", number="ALIM-2026-000002", date=date(2026, 8, 21),
            due_date=date(2026, 9, 21),
        )
        InvoiceItem.objects.create(
            invoice=self.invoice, line_no=1, description="Baklava ecru 305",
            quantity=Decimal("55.000"), unit="mt", unit_price=Decimal("3.50"),
            product=product, variant=self.variant,
        )

    def _html(self):
        resp = self.client.get(
            reverse("accounts:purchase_order_detail", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_sku_and_every_attribute_get_their_own_row(self):
        html = self._html()
        self.assertIn("<dt>SKU</dt>", html)
        self.assertIn('<dd class="sku">S-BAKLAVA.R1106ECRU-305</dd>', html)
        # Each attribute is named where its value is shown.
        self.assertIn("<dt>Color</dt>", html)
        self.assertIn("<dd>r-1106-ecru</dd>", html)
        self.assertIn("<dt>Width</dt>", html)
        self.assertIn("<dd>305</dd>", html)

    def test_attributes_read_in_the_same_order_on_every_line(self):
        html = self._html()
        # Sorted by attribute name, so a page of lines can be scanned down
        # a column rather than re-read per line.
        self.assertLess(html.index("<dt>Color</dt>"), html.index("<dt>Width</dt>"))

    def test_a_second_line_costs_no_extra_attribute_query(self):
        """Every line's attributes are fetched once, for the whole page.

        A purchase routinely runs to dozens of lines; reading the values
        per line would put a query behind each one.
        """
        url = reverse("accounts:purchase_order_detail", args=[self.invoice.pk])
        self.client.get(url)  # warm whatever the shell caches
        with CaptureQueriesContext(connection) as one_line:
            self.client.get(url)

        second = ProductVariant.objects.create(
            product=self.variant.product, variant_sku="S-BAKLAVA.LT6186GRAY-300")
        for name, value in (("width", "300"), ("color", "lt-6186-gray")):
            attribute = ProductVariantAttribute.objects.get(name=name)
            second.product_variant_attribute_values.add(
                ProductVariantAttributeValue.objects.create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=value,
                )
            )
        InvoiceItem.objects.create(
            invoice=self.invoice, line_no=2, description="Baklava gray 300",
            quantity=Decimal("40.000"), unit="mt", unit_price=Decimal("3.50"),
            product=self.variant.product, variant=second,
        )

        with CaptureQueriesContext(connection) as two_lines:
            resp = self.client.get(url)
        self.assertContains(resp, "lt-6186-gray")
        self.assertEqual(len(two_lines), len(one_line))
