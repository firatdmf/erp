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


class DraftPurchaseExpectedRollsTest(TestCase):
    """A purchase not yet received has no rolls in the warehouse, but its
    order says which it expects and roughly how long each is. The page
    lists those, marked approximate, until the real ones arrive."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.user = get_user_model().objects.create_superuser(
            username="draft_buyer", password="pw", email="d@a.c")
        self.client.force_login(self.user)
        self.invoice = Invoice.objects.create(
            book=self.book, current_account=self.supplier, currency=self.usd,
            type="purchase", status="draft", number="PUR-000142",
            date=date(2026, 9, 29), due_date=date(2026, 10, 29),
            intake_warehouse=self.wh,
            intake_plan={"products": [{
                "unit": "mt", "pack_type": "roll",
                "main_product": {"mode": "new", "name": "MT-5019"},
                "variants": [
                    {"sku": "MRK0013", "name": "ecru", "price": "2.50",
                     "tops": [{"qty": 30, "barcode": ""}, {"qty": "27,5", "barcode": ""}]},
                    # No metres entered: no line, so it must not shift the
                    # next variant's rolls onto the wrong line.
                    {"sku": "MRK0014", "name": "white", "price": "2.50",
                     "tops": [{"qty": "", "barcode": ""}]},
                    {"sku": "MRK0015", "name": "grey", "price": "2.50",
                     "tops": [{"qty": 40, "barcode": "MRK000123"}]},
                ],
            }]},
        )
        for n, (desc, qty) in enumerate([("MT-5019 ecru", "57.5"), ("MT-5019 grey", "40")], 1):
            InvoiceItem.objects.create(
                invoice=self.invoice, line_no=n, description=desc,
                quantity=Decimal(qty), unit="mt", unit_price=Decimal("2.50"))

    def _html(self):
        resp = self.client.get(
            reverse("accounts:purchase_order_detail", args=[self.invoice.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode().split("</style>", 1)[1]

    def test_each_line_lists_the_rolls_it_expects(self):
        html = self._html()
        ecru, grey = html.split('class="po-item"')[1:3]
        self.assertIn('<span class="po-rolls-n">2 rolls</span>', ecru)
        self.assertIn("≈ 30.00 m", ecru)
        self.assertIn("≈ 27.50 m", ecru)
        self.assertIn('<span class="po-rolls-n">1 roll</span>', grey)
        self.assertIn("≈ 40.00 m", grey)
        self.assertIn("<code>MRK000123</code>", grey)

    def test_they_are_marked_expected_not_received(self):
        html = self._html()
        self.assertIn("Expected rolls — approximate", html)
        self.assertNotIn("Physical rolls received", html)
        self.assertNotIn("roll barcodes", html)
        self.assertNotIn("No rolls linked", html)

    def test_the_total_counts_the_expected_rolls(self):
        self.assertRegex(self._html(), r'97\.50 mt\s*<span class="dot">·</span>\s*3 rolls')

    def test_the_card_names_the_product_and_its_skus(self):
        """Picked from the catalog, the form sends the product's title and
        no name; the card must still say which product the line is of."""
        mt = Product.objects.create(title="MT-5019", sku="MT-5019")
        plan = self.invoice.intake_plan
        plan["products"][0]["main_product"] = {
            "mode": "existing", "id": mt.pk, "title": "MT-5019", "sku": "MT-5019"}
        plan["products"][0]["variants"][0]["attributes"] = [{"name": "color", "value": "ecru"}]
        self.invoice.intake_plan = plan
        self.invoice.save(update_fields=["intake_plan"])
        # As it was stored before plan_lines() read the title.
        self.invoice.items.filter(line_no=1).update(description="ecru")
        ecru = self._html().split('class="po-item"')[1]
        self.assertIn('<span class="po-item-name">MT-5019 ecru</span>', ecru)
        self.assertRegex(ecru, r'Product SKU</dt>\s*<dd class="sku">MT-5019</dd>')
        self.assertRegex(ecru, r'<dt>SKU</dt>\s*<dd class="sku">MRK0013</dd>')
        self.assertRegex(ecru, r'<dt>Color</dt>\s*<dd>ecru</dd>')

    def test_a_saved_line_is_described_with_its_product(self):
        from accounting.views_purchase import plan_lines
        mt = Product.objects.create(title="MT-5019", sku="MT-5019")
        plan = {"products": [{"main_product": {"mode": "existing", "id": mt.pk,
                                               "title": "MT-5019", "sku": "MT-5019"},
                              "variants": [{"sku": "MRK0013", "name": "ecru",
                                            "tops": [{"qty": 30}]}]}]}
        self.assertEqual(plan_lines(plan)[0]["description"], "MT-5019 ecru")
