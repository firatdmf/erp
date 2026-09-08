# to run this test, use the command:
# python manage.py test marketing.tests.test_purge_legacy_catalog_import

import json
import tempfile
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounting.models import Book
from marketing.models import Product, ProductFile, ProductVariant
from operating.models import Order, OrderItem, Warehouse, WarehouseProduct


class PurgeLegacyCatalogImportTest(TestCase):
    """The 2026-07-06 home-textile load is selected by SKU shape and by never
    having been in a warehouse. Everything else in the command is a guard: if
    the shape catches something real, that row is spared rather than the
    selection widened.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wh = Warehouse.objects.create(
            name="Laleli Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

        # A pure legacy product: every variant is shape-matching and shelfless.
        self.junk = Product.objects.create(title="GÜRSAN", featured=False)
        self.j1 = self._legacy(self.junk, "B00000001", "17.50")
        self.j2 = self._legacy(self.junk, "DN0000968", "9.55")

        # A mixed product — the shape of LOVE / KADİFE / DMF / ADEM in prod.
        self.mixed = Product.objects.create(title="KADİFE", featured=False)
        self.stray = self._legacy(self.mixed, "H00001122", "4.00")
        self.real = ProductVariant.objects.create(
            product=self.mixed, variant_sku="K24592.G28")

    def _legacy(self, product, sku, cost):
        """As the real rows are: unfeatured and unpriced. variant_featured
        defaults to True on the model, and the purge guards on it — so a
        fixture that forgets this is spared, exactly as it should be."""
        return ProductVariant.objects.create(
            product=product, variant_sku=sku, variant_cost=Decimal(cost),
            variant_featured=False)
        WarehouseProduct.objects.create(
            warehouse=self.wh, name="x", sku="K24592.G28",
            quantity=Decimal("60.60"), catalog_variant=self.real)

    def _run(self, apply=False):
        out = StringIO()
        call_command("purge_legacy_catalog_import", *(["--apply"] if apply else []),
                     "--backup-dir", self.tmp, stdout=out)
        return out.getvalue()

    def test_the_dry_run_deletes_nothing(self):
        self._run()
        self.assertEqual(ProductVariant.objects.count(), 4)
        self.assertEqual(Product.objects.count(), 2)

    def test_it_removes_the_legacy_variants(self):
        self._run(apply=True)
        self.assertFalse(ProductVariant.objects.filter(
            pk__in=[self.j1.pk, self.j2.pk, self.stray.pk]).exists())

    def test_a_product_emptied_by_the_purge_goes_too(self):
        self._run(apply=True)
        self.assertFalse(Product.objects.filter(pk=self.junk.pk).exists())

    def test_a_product_that_still_holds_a_real_variant_stays(self):
        """KADİFE carries stray legacy variants beside stocked ones. It keeps
        its stocked variant and its row."""
        self._run(apply=True)
        self.assertTrue(Product.objects.filter(pk=self.mixed.pk).exists())
        self.assertEqual(
            list(self.mixed.variants.values_list("variant_sku", flat=True)),
            ["K24592.G28"])

    def test_a_stocked_variant_is_never_selected_even_with_a_legacy_sku(self):
        v = self._legacy(self.mixed, "P00000048", "1")
        WarehouseProduct.objects.create(
            warehouse=self.wh, name="y", sku="P00000048",
            quantity=Decimal("3"), catalog_variant=v)
        self._run(apply=True)
        self.assertTrue(ProductVariant.objects.filter(pk=v.pk).exists())

    def test_a_featured_or_priced_row_is_spared_and_reported(self):
        keep = ProductVariant.objects.create(
            product=self.junk, variant_sku="Y00000933",
            variant_cost=Decimal("2"), variant_featured=True)
        priced = ProductVariant.objects.create(
            product=self.junk, variant_sku="Y00000934", variant_featured=False,
            variant_cost=Decimal("2"), variant_price=Decimal("10"))
        out = self._run(apply=True)
        self.assertTrue(ProductVariant.objects.filter(pk=keep.pk).exists())
        self.assertTrue(ProductVariant.objects.filter(pk=priced.pk).exists())
        self.assertIn("SPARED", out)
        # and the product that still holds them survives
        self.assertTrue(Product.objects.filter(pk=self.junk.pk).exists())

    def test_a_row_on_an_order_line_is_spared(self):
        order = Order.objects.create(order_number="DK-PURGE")
        OrderItem.objects.create(order=order, product=self.junk,
                                 product_variant=self.j1,
                                 quantity=Decimal("1"), price=Decimal("1"))
        self._run(apply=True)
        self.assertTrue(ProductVariant.objects.filter(pk=self.j1.pk).exists())

    def test_a_product_with_images_is_kept_even_when_emptied(self):
        ProductFile.objects.create(product=self.junk, file_url="x/img.avif")
        self._run(apply=True)
        self.assertTrue(Product.objects.filter(pk=self.junk.pk).exists())

    def test_it_writes_a_restorable_snapshot_before_deleting(self):
        import glob
        self._run(apply=True)
        files = glob.glob(f"{self.tmp}/legacy-catalog-import-purged-*.json")
        self.assertEqual(len(files), 1, files)
        doc = json.load(open(files[0], encoding="utf-8"))
        by_sku = {v["variant_sku"]: v for v in doc["product_variants"]}
        self.assertIn("B00000001", by_sku)
        self.assertEqual(by_sku["B00000001"]["variant_cost"], "17.50")
        self.assertTrue(all("id" in v for v in doc["product_variants"]))
        self.assertIn(self.junk.pk, [p["id"] for p in doc["products"]])

    def test_running_it_twice_is_a_no_op(self):
        self._run(apply=True)
        out = self._run(apply=True)
        self.assertIn("Nothing to do", out)
