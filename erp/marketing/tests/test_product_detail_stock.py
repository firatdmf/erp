# to run this test, use the command:
# python manage.py test marketing.tests.test_product_detail_stock

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductVariant
from operating.models import Warehouse, WarehouseProduct


class ProductDetailStockTest(TestCase):
    """The variants table prints the metres the warehouse holds.

    It used to bucket them the way a storefront does — "50+" or nothing —
    which told the people who sell and cut the cloth that a variant with
    forty metres on the shelf was "unavailable".
    """

    def setUp(self):
        self.book = Book.objects.create(name="Demfirat")
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.product = Product.objects.create(title="Baklava", unit="mt")
        self.user = get_user_model().objects.create_superuser(
            username="stock_reader", password="pw", email="s@a.c")
        self.client.force_login(self.user)

    def _variant(self, sku, quantity=None):
        variant = ProductVariant.objects.create(product=self.product, variant_sku=sku)
        if quantity is not None:
            WarehouseProduct.objects.create(
                warehouse=self.warehouse, name=sku, sku=sku,
                quantity=Decimal(quantity), catalog_variant=variant)
        return variant

    def _html(self):
        return self.client.get(
            reverse("marketing:product_detail", args=[self.product.pk])).content.decode()

    def test_a_variant_shows_what_the_warehouse_holds(self):
        self._variant("S-BAKLAVA.ECRU-305", "40.00")
        html = self._html()
        self.assertIn("<b>40</b> m", html)
        # Forty metres is stock, not an absence of it.
        self.assertNotIn("Unavailable", html)

    def test_stock_in_two_warehouses_is_added_up_and_each_one_named(self):
        variant = self._variant("S-BAKLAVA.GRAY-300", "120.50")
        other = Warehouse.objects.create(name="Depo", accounting_book=self.book)
        WarehouseProduct.objects.create(
            warehouse=other, name="x", sku="S-BAKLAVA.GRAY-300.2",
            quantity=Decimal("9.50"), catalog_variant=variant)
        html = self._html()
        self.assertIn("<b>130</b> m", html)
        for warehouse, quantity in (("Fabrika", "120.50"), ("Depo", "9.50")):
            self.assertIn(warehouse, html)
            self.assertIn(f'<span class="q">{quantity}</span>', html)

    def test_a_total_spanning_two_books_says_whose_metres_they_are(self):
        """Laleli's cloth and Ergene's are not one pile to cut from."""
        variant = self._variant("K24614.G47", "143.50")
        ergene = Book.objects.create(name="Ergene Fabric")
        WarehouseProduct.objects.create(
            warehouse=Warehouse.objects.create(name="Ergene Fabrika", accounting_book=ergene),
            name="x", sku="K24614.G47.2", quantity=Decimal("479.10"), catalog_variant=variant)
        html = self._html()
        self.assertIn("<b>622.60</b> m", html)
        self.assertIn("Ergene Fabrika", html)
        self.assertIn('<span class="q">479.10</span>', html)

    def test_one_warehouse_holding_the_lot_needs_no_breakdown(self):
        self._variant("S-BAKLAVA.ONE-305", "40.00")
        # (the class name also appears in the page's stylesheet)
        self.assertNotIn('class="stock-where"', self._html())

    def test_nothing_left_reads_out_of_stock_and_no_warehouse_row_reads_made_to_order(self):
        self._variant("S-BAKLAVA.EMPTY-305", "0.00")
        self._variant("S-BAKLAVA.NEVER-305")
        html = self._html()
        self.assertIn("Out of stock", html)
        self.assertIn("Made to order", html)

    def test_a_second_variant_costs_no_extra_query(self):
        self._variant("S-BAKLAVA.ONE-305", "40.00")
        url = reverse("marketing:product_detail", args=[self.product.pk])
        self.client.get(url)  # warm whatever the shell caches
        with CaptureQueriesContext(connection) as one:
            self.client.get(url)

        self._variant("S-BAKLAVA.TWO-300", "12.00")
        with CaptureQueriesContext(connection) as two:
            resp = self.client.get(url)
        self.assertContains(resp, "<b>12</b> m")
        self.assertEqual(len(two), len(one))
