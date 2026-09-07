# to run this test, use the command:
# python manage.py test marketing.tests.test_live_quantity

from decimal import Decimal

from django.test import TestCase

from accounting.models import Book
from marketing.models import (Product, ProductVariant, with_live_quantity,
                              with_product_live_quantity)
from operating.models import Warehouse, WarehouseProduct


def _warehouse(name):
    return Warehouse.objects.create(
        name=name, accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])


class LiveQuantityTest(TestCase):
    """A variant's stock is what the warehouse holds, read at the moment it
    is asked for. There is no stored counterpart any more — the column had
    five writers, which is how 181 rows drifted out of step and 1,507
    variants with nothing behind them advertised 31,533 metres that did not
    exist.
    """

    def setUp(self):
        self.wh1 = _warehouse("Fabrika")
        self.wh2 = _warehouse("Laleli")
        self.product = Product.objects.create(title="N1464T", sku="N1464T", featured=False)

    def _variant(self, sku):
        return ProductVariant.objects.create(product=self.product, variant_sku=sku)

    def _row(self, variant, warehouse, qty):
        return WarehouseProduct.objects.create(
            warehouse=warehouse, name=variant.variant_sku, sku=variant.variant_sku,
            quantity=Decimal(qty), catalog_variant=variant)

    def test_it_sums_every_warehouse_holding_the_sku(self):
        """The bug this replaces: the mirror held ONE warehouse's number, so
        a SKU in two depots reported only the last one synced."""
        v = self._variant("N1464T.G01")
        self._row(v, self.wh1, "2013.60")
        self._row(v, self.wh2, "22.00")
        self.assertEqual(v.live_quantity, Decimal("2035.60"))

    def test_an_emptied_warehouse_row_reads_zero(self):
        v = self._variant("N1464T.G54")
        self._row(v, self.wh1, "0.00")
        self.assertEqual(v.live_quantity, Decimal("0.00"))
        self.assertIs(v.stock_tracked, True)

    def test_a_variant_no_warehouse_carries_has_no_quantity(self):
        """None, not zero. "We hold none of it" and "we make it to order"
        are different answers to a buyer, and stock_tracked separates them."""
        v = self._variant("WEBONLY-1")
        self.assertIsNone(v.live_quantity)
        self.assertIs(v.stock_tracked, False)

    def test_the_annotation_agrees_with_the_properties(self):
        a = self._variant("N1464T.G02")
        self._row(a, self.wh1, "10.00")
        self._row(a, self.wh2, "5.50")
        b = self._variant("WEBONLY-3")

        rows = {v.variant_sku: v for v in with_live_quantity(ProductVariant.objects.all())}
        self.assertEqual(rows["N1464T.G02"].live_quantity, a.live_quantity)
        self.assertEqual(rows["N1464T.G02"].live_quantity, Decimal("15.50"))
        self.assertIs(rows["N1464T.G02"].stock_tracked, True)
        self.assertIsNone(rows["WEBONLY-3"].live_quantity)
        self.assertIs(rows["WEBONLY-3"].stock_tracked, b.stock_tracked)

    def test_the_annotation_costs_one_query(self):
        for i in range(5):
            v = self._variant(f"N1464T.Q{i}")
            self._row(v, self.wh1, "3.00")
        with self.assertNumQueries(1):
            total = [v.live_quantity for v in with_live_quantity(ProductVariant.objects.all())]
        self.assertEqual(total.count(Decimal("3.00")), 5)


class ProductLiveQuantityTest(TestCase):
    """A product's stock is everything the warehouse holds across its
    variants. Product.quantity is gone, so there is nothing to drift."""

    def setUp(self):
        self.wh = _warehouse("Fabrika")
        self.product = Product.objects.create(title="K12504", sku="K12504", featured=False)
        self.empty = Product.objects.create(title="MADE-TO-ORDER", sku="MTO", featured=True)

    def _stocked(self, sku, qty):
        v = ProductVariant.objects.create(product=self.product, variant_sku=sku)
        WarehouseProduct.objects.create(
            warehouse=self.wh, name=sku, sku=sku,
            quantity=Decimal(qty), catalog_variant=v)
        return v

    def test_it_adds_up_every_variant(self):
        self._stocked("K12504.G07", "10.00")
        self._stocked("K12504.G28", "32.50")
        self.assertEqual(self.product.live_quantity, Decimal("42.50"))

    def test_a_product_no_warehouse_carries_is_none(self):
        ProductVariant.objects.create(product=self.empty, variant_sku="MTO-1")
        self.assertIsNone(self.empty.live_quantity)

    def test_the_annotation_agrees_with_the_property(self):
        self._stocked("K12504.G47", "7.25")
        rows = {p.title: p for p in
                with_product_live_quantity(Product.objects.all())}
        self.assertEqual(rows["K12504"].live_quantity, self.product.live_quantity)
        self.assertEqual(rows["K12504"].live_quantity, Decimal("7.25"))
        self.assertIsNone(rows["MADE-TO-ORDER"].live_quantity)

    def test_the_annotation_does_not_multiply_by_a_second_join(self):
        """Summing across variants with anything else multi-valued joined in
        would count each variant's metres once per joined row. A subquery
        cannot, which is why it is one."""
        from django.db.models import Count
        self._stocked("K12504.G50", "10.00")
        self._stocked("K12504.G52", "10.00")
        row = (with_product_live_quantity(Product.objects.filter(pk=self.product.pk))
               .annotate(n=Count("variants")).get())
        self.assertEqual(row.n, 2)
        self.assertEqual(row.live_quantity, Decimal("20.00"))


class StorefrontApiReadsLiveQuantityTest(TestCase):
    """The storefront builds variants with raw SQL, so the derivation has to
    live in the query — a model property alone would never reach it."""

    def setUp(self):
        self.wh1 = _warehouse("Fabrika")
        self.wh2 = _warehouse("Laleli")
        self.product = Product.objects.create(title="Tulle", sku="TTEMPILISE", featured=True)
        self.stocked = ProductVariant.objects.create(
            product=self.product, variant_sku="ONRKZL000050")
        for wh, qty in ((self.wh1, "2013.60"), (self.wh2, "22.00")):
            WarehouseProduct.objects.create(
                warehouse=wh, name="x", sku="ONRKZL000050", quantity=Decimal(qty),
                catalog_variant=self.stocked)
        self.web_only = ProductVariant.objects.create(
            product=self.product, variant_sku="WEBONLY-9")

    def _get(self):
        import json
        r = self.client.get("/marketing/api/get_product", {"product_sku": "TTEMPILISE"},
                            headers={"host": "testserver"})
        self.assertEqual(r.status_code, 200, r.content[:200])
        return json.loads(r.content)

    def test_it_flags_which_variants_the_warehouse_carries(self):
        """stock_tracked drives the storefront's "Manufactured on demand"
        line — a variant with no warehouse row has no quantity to quote, and
        must not read as out of stock."""
        by_sku = {v["variant_sku"]: v for v in self._get()["product_variants"]}
        self.assertIs(by_sku["ONRKZL000050"]["stock_tracked"], True)
        self.assertIs(by_sku["WEBONLY-9"]["stock_tracked"], False)

    def test_the_detail_endpoint_serves_the_derived_number(self):
        by_sku = {v["variant_sku"]: v["variant_quantity"]
                  for v in self._get()["product_variants"]}
        self.assertAlmostEqual(by_sku["ONRKZL000050"], 2035.60, places=2)
        self.assertIsNone(by_sku["WEBONLY-9"],
                          "no warehouse carries it, so there is no number to quote")

    def test_the_product_level_quantity_is_derived_too(self):
        """p.quantity is gone from the table; the endpoint still answers with
        everything the warehouse holds across the product's variants."""
        self.assertAlmostEqual(self._get()["product"]["quantity"], 2035.60, places=2)
