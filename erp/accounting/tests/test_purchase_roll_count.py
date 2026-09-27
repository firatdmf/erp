# to run this test, use the command:
# python manage.py test accounting.tests.test_purchase_roll_count

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, InvoiceItem
from marketing.models import Product, ProductVariant
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class PurchaseLineRollCountTest(TestCase):
    """Each purchased line says how many rolls it came in as.

    The receiver counts the rolls on the pallet before reading a single
    barcode, and the metres on the line do not tell them what number to
    expect — the same 55 m can be two rolls or five. A line of fitted
    sheets is counted in boxes, not rolls: the page names the stock items
    by the product's own pack.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.user = get_user_model().objects.create_superuser(
            username="count_buyer", password="pw", email="c@a.c")
        self.client.force_login(self.user)

        self.invoice = Invoice.objects.create(
            book=self.book, current_account=self.supplier, currency=self.usd,
            type="purchase", number="ALIM-2026-000003", date=date(2026, 8, 21),
            due_date=date(2026, 9, 21), intake_warehouse=self.wh,
        )
        self.product = WarehouseProduct.objects.create(
            warehouse=self.wh, name="K24644 G07", sku="K24644.G07",
            quantity=Decimal("95.00"))

    def _line(self, line_no, metres, product=None, stock=None, unit="mt"):
        item = InvoiceItem.objects.create(
            invoice=self.invoice, line_no=line_no, description=f"Line {line_no}",
            quantity=sum(metres), unit=unit, unit_price=Decimal("3.50"),
            product=product,
        )
        for i, m in enumerate(metres, 1):
            WarehouseProductItem.objects.create(
                product=stock or self.product, quantity=m,
                barcode=f"KRV{line_no}{i:06d}", purchase_invoice_item=item)
        return item

    def _html(self):
        resp = self.client.get(
            reverse("accounts:purchase_order_detail", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_each_card_counts_its_own_rolls(self):
        self._line(1, [Decimal("30.00"), Decimal("25.00")])
        self._line(2, [Decimal("15.00"), Decimal("15.00"), Decimal("10.00")])
        html = self._html()
        self.assertIn('<span class="po-rolls-n">2 rolls</span>', html)
        self.assertIn('<span class="po-rolls-n">3 rolls</span>', html)

    def test_a_single_roll_is_not_pluralised(self):
        self._line(1, [Decimal("55.00")])
        self.assertIn('<span class="po-rolls-n">1 roll</span>', self._html())

    def test_a_line_without_rolls_shows_no_count(self):
        InvoiceItem.objects.create(
            invoice=self.invoice, line_no=1, description="Ordered, not here",
            quantity=Decimal("55.000"), unit="mt", unit_price=Decimal("3.50"),
        )
        html = self._html()
        self.assertNotIn("po-rolls-n", html.split("</style>", 1)[1])
        self.assertIn("No rolls linked to this line yet.", html)

    def test_a_boxed_product_is_counted_in_boxes(self):
        sheets = Product.objects.create(title="Fitted sheet", unit="piece", pack_type="box")
        variant = ProductVariant.objects.create(product=sheets, variant_sku="FS-160")
        stock = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Fitted sheet 160", sku="FS-160",
            quantity=Decimal("24.00"), catalog_variant=variant)
        self._line(1, [Decimal("12.00"), Decimal("12.00")],
                   product=sheets, stock=stock, unit="piece")
        html = self._html()
        self.assertIn('<span class="po-rolls-n">2 boxes</span>', html)
        self.assertIn("Physical boxes received", html)
        self.assertIn("Print box barcodes", html)
        self.assertIn("12.00 pcs", html)
        self.assertNotIn("rolls received", html)
        self.assertNotIn("roll barcodes", html)

    def test_a_free_text_line_takes_its_pack_from_the_stock(self):
        """The line has no catalog product; its stock rows still do."""
        sheets = Product.objects.create(title="Fitted sheet", unit="piece", pack_type="bag")
        variant = ProductVariant.objects.create(product=sheets, variant_sku="FS-180")
        stock = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Fitted sheet 180", sku="FS-180",
            quantity=Decimal("6.00"), catalog_variant=variant)
        self._line(1, [Decimal("6.00")], stock=stock, unit="piece")
        self.assertIn('<span class="po-rolls-n">1 bag</span>', self._html())
