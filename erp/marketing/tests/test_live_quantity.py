# to run this test, use the command:
# python manage.py test marketing.tests.test_live_quantity

from decimal import Decimal

from django.test import TestCase

from marketing.models import Product, ProductVariant, with_live_quantity
from operating.models import Warehouse, WarehouseProduct


class LiveQuantityTest(TestCase):
    """A variant's stock is what the warehouse holds, read at the moment it
    is asked for — not a number mirrored into a column by five different
    writers, which is how 81 rows drifted and 2,978 variants with nothing
    behind them ended up advertising stock.
    """

    def setUp(self):
        self.wh1 = Warehouse.objects.create(name="Fabrika")
        self.wh2 = Warehouse.objects.create(name="Laleli")
        self.product = Product.objects.create(title="N1464T", sku="N1464T", featured=False)

    def _variant(self, sku, stored):
        return ProductVariant.objects.create(
            product=self.product, variant_sku=sku, variant_quantity=Decimal(stored))

    def _row(self, variant, warehouse, qty):
        return WarehouseProduct.objects.create(
            warehouse=warehouse, name=variant.variant_sku, sku=variant.variant_sku,
            quantity=Decimal(qty), catalog_variant=variant)

    def test_it_sums_every_warehouse_holding_the_sku(self):
        """The bug this replaces: the mirror held ONE warehouse's number, so
        a SKU in two depots reported only the last one synced."""
        v = self._variant("N1464T.G01", "22.00")
        self._row(v, self.wh1, "2013.60")
        self._row(v, self.wh2, "22.00")
        self.assertEqual(v.live_quantity, Decimal("2035.60"))

    def test_a_stale_stored_value_is_ignored(self):
        v = self._variant("N1464T.G54", "33.66")
        self._row(v, self.wh1, "0.00")
        self.assertEqual(v.live_quantity, Decimal("0.00"))

    def test_a_variant_the_warehouse_does_not_carry_keeps_its_own_count(self):
        """Storefront-only goods are kept by CSV import and the stock API —
        deriving those from warehouse rows would zero 74 live items."""
        v = self._variant("WEBONLY-1", "102.00")
        self.assertEqual(v.live_quantity, Decimal("102.00"))

    def test_no_rows_and_no_stored_value_is_None(self):
        v = self._variant("WEBONLY-2", "0")
        v.variant_quantity = None
        v.save(update_fields=["variant_quantity"])
        self.assertIsNone(v.live_quantity)

    def test_the_annotation_agrees_with_the_property(self):
        a = self._variant("N1464T.G02", "1.00")
        self._row(a, self.wh1, "10.00")
        self._row(a, self.wh2, "5.50")
        b = self._variant("WEBONLY-3", "7.25")

        rows = {v.variant_sku: v for v in with_live_quantity(ProductVariant.objects.all())}
        self.assertEqual(rows["N1464T.G02"].live_quantity, a.live_quantity)
        self.assertEqual(rows["N1464T.G02"].live_quantity, Decimal("15.50"))
        self.assertEqual(rows["WEBONLY-3"].live_quantity, b.live_quantity)
        self.assertEqual(rows["WEBONLY-3"].live_quantity, Decimal("7.25"))

    def test_the_annotation_costs_one_query(self):
        for i in range(5):
            v = self._variant(f"N1464T.Q{i}", "1.00")
            self._row(v, self.wh1, "3.00")
        with self.assertNumQueries(1):
            total = [v.live_quantity for v in with_live_quantity(ProductVariant.objects.all())]
        self.assertEqual(total.count(Decimal("3.00")), 5)


class StorefrontApiReadsLiveQuantityTest(TestCase):
    """The storefront builds variants with raw SQL, so the derivation has to
    live in the query — a model property alone would never reach it."""

    def setUp(self):
        self.wh1 = Warehouse.objects.create(name="Fabrika")
        self.wh2 = Warehouse.objects.create(name="Laleli")
        self.product = Product.objects.create(title="Tulle", sku="TTEMPILISE", featured=True)
        self.stocked = ProductVariant.objects.create(
            product=self.product, variant_sku="ONRKZL000050", variant_quantity=Decimal("22.00"))
        for wh, qty in ((self.wh1, "2013.60"), (self.wh2, "22.00")):
            WarehouseProduct.objects.create(
                warehouse=wh, name="x", sku="ONRKZL000050", quantity=Decimal(qty),
                catalog_variant=self.stocked)
        self.web_only = ProductVariant.objects.create(
            product=self.product, variant_sku="WEBONLY-9", variant_quantity=Decimal("102.00"))

    def test_it_flags_which_variants_the_warehouse_carries(self):
        """stock_tracked drives the storefront's "Manufactured on demand"
        line — a variant with no warehouse row has no quantity to quote, and
        must not read as out of stock."""
        import json
        r = self.client.get("/marketing/api/get_product", {"product_sku": "TTEMPILISE"},
                            headers={"host": "testserver"})
        by_sku = {v["variant_sku"]: v for v in json.loads(r.content)["product_variants"]}
        self.assertIs(by_sku["ONRKZL000050"]["stock_tracked"], True)
        self.assertIs(by_sku["WEBONLY-9"]["stock_tracked"], False)

    def test_the_detail_endpoint_serves_the_derived_number(self):
        import json
        r = self.client.get("/marketing/api/get_product", {"product_sku": "TTEMPILISE"},
                            headers={"host": "testserver"})
        self.assertEqual(r.status_code, 200, r.content[:200])
        by_sku = {v["variant_sku"]: v["variant_quantity"]
                  for v in json.loads(r.content)["product_variants"]}
        self.assertAlmostEqual(by_sku["ONRKZL000050"], 2035.60, places=2)
        self.assertAlmostEqual(by_sku["WEBONLY-9"], 102.00, places=2)
