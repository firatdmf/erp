# to run this test, use the command:
# python manage.py test accounting.test_purchase_roll_labels

import re
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, Invoice, InvoiceItem
from operating.models import Warehouse, WarehouseProduct, WarehouseProductRoll


class PurchaseLineLabelsTest(TestCase):
    """The rolls of a delivery get their stickers from the delivery.

    They arrive together and are labelled together, so the purchase line
    prints every roll on it in one PDF — the warehouseman no longer has to
    open each product's own page to print the same labels.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.user = get_user_model().objects.create_superuser(
            username="label_buyer", password="pw", email="b@a.c")
        self.client.force_login(self.user)

        self.invoice = Invoice.objects.create(
            book=self.book, cari=self.cari, currency=self.usd, type="purchase",
            number="ALIM-2026-000001", date=date(2026, 8, 21),
            due_date=date(2026, 9, 21), intake_warehouse=self.wh,
        )
        self.item = InvoiceItem.objects.create(
            invoice=self.invoice, line_no=1, description="K24644 G07",
            quantity=Decimal("55.000"), unit="mt", unit_price=Decimal("3.50"),
        )
        self.product = WarehouseProduct.objects.create(
            warehouse=self.wh, name="K24644 G07", sku="K24644.G07",
            quantity=Decimal("55.00"))
        self.rolls = [
            WarehouseProductRoll.objects.create(
                product=self.product, meters=Decimal("30.00"),
                barcode="KRV0000001", purchase_invoice_item=self.item),
            WarehouseProductRoll.objects.create(
                product=self.product, meters=Decimal("25.00"),
                barcode="KRV0000002", purchase_invoice_item=self.item),
        ]

        # reportlab flate-compresses page streams by default, which would
        # hide the drawn strings from a byte search. Off for the test only.
        import reportlab.rl_config as rl_config
        compression = rl_config.pageCompression
        rl_config.pageCompression = 0
        self.addCleanup(setattr, rl_config, "pageCompression", compression)

    def _url(self, item=None):
        return reverse("accounts:purchase_item_labels",
                       args=[self.invoice.pk, (item or self.item).pk])

    def _drawn(self, resp):
        # Every string the canvas draws lands in the page stream as "(text) Tj".
        return [s.decode("latin-1") for s in re.findall(rb"\((.*?)\)\s*Tj", resp.content)]

    def test_one_page_per_roll_on_the_line(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("inline", resp["Content-Disposition"])
        drawn = self._drawn(resp)
        self.assertIn("KRV0000001", drawn)
        self.assertIn("KRV0000002", drawn)
        self.assertIn("30.00", drawn)
        self.assertIn("25.00", drawn)

    def test_rolls_of_other_lines_stay_out(self):
        other_item = InvoiceItem.objects.create(
            invoice=self.invoice, line_no=2, description="K24644 G09",
            quantity=Decimal("12.000"), unit="mt", unit_price=Decimal("3.50"))
        WarehouseProductRoll.objects.create(
            product=self.product, meters=Decimal("12.00"),
            barcode="KRV0000003", purchase_invoice_item=other_item)

        drawn = self._drawn(self.client.get(self._url()))
        self.assertNotIn("KRV0000003", drawn)
        self.assertIn("KRV0000003", self._drawn(self.client.get(self._url(other_item))))

    def test_each_roll_carries_its_own_product(self):
        # A line's rolls can land on more than one warehouse product (two
        # variants of the same fabric, say); every page must name the
        # product its own roll sits on, not the first one's.
        other_product = WarehouseProduct.objects.create(
            warehouse=self.wh, name="K24644 G11", sku="K24644.G11",
            quantity=Decimal("8.00"))
        WarehouseProductRoll.objects.create(
            product=other_product, meters=Decimal("8.00"),
            barcode="KRV0000004", purchase_invoice_item=self.item)

        drawn = self._drawn(self.client.get(self._url()))
        self.assertIn("K24644.G07", drawn)
        self.assertIn("K24644.G11", drawn)

    def test_line_without_rolls_has_nothing_to_print(self):
        empty = InvoiceItem.objects.create(
            invoice=self.invoice, line_no=3, description="Nakliye",
            quantity=Decimal("1.000"), unit="pcs", unit_price=Decimal("50.00"))
        self.assertEqual(self.client.get(self._url(empty)).status_code, 404)

    def test_an_item_of_another_invoice_is_not_reachable(self):
        other = Invoice.objects.create(
            book=self.book, cari=self.cari, currency=self.usd, type="purchase",
            number="ALIM-2026-000002", date=date(2026, 8, 22),
            due_date=date(2026, 9, 22))
        url = reverse("accounts:purchase_item_labels", args=[other.pk, self.item.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_the_button_is_on_the_purchase_page(self):
        page = self.client.get(reverse("accounts:purchase_order_detail",
                                       args=[self.invoice.pk]))
        self.assertContains(page, self._url())
