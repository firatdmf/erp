# to run this test, use the command:
# python manage.py test operating.test_merge_product_families

from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from accounting.models import Book
from marketing.models import Product, ProductFile, ProductVariant
from operating.models import (Order, OrderItem, Warehouse, WarehouseProduct)


class MergeProductFamiliesTest(TestCase):
    """The same fabric under two Product rows: a featured web product with
    the images, and a hidden husk minted under the correct code. The
    featured row survives and takes the code, because it is the one the
    storefront links to and the one holding the files.
    """

    MERGES = [("24592", "K24592", "K24592", "K24592")]

    def setUp(self):
        self.wh = Warehouse.objects.create(
            name="Laleli Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

        self.featured = Product.objects.create(
            title="24592", sku="24592", featured=True)
        self.hidden = Product.objects.create(
            title="K24592", sku="K24592", featured=False)

        ProductFile.objects.create(product=self.featured, file_url="x/img.avif")

        self.kept = self._variant(self.featured, "K24592.G28", "60.60")
        self.moved = self._variant(self.hidden, "K24592.G07", "102.30")

    def _variant(self, product, sku, qty):
        v = ProductVariant.objects.create(product=product, variant_sku=sku)
        WarehouseProduct.objects.create(
            warehouse=self.wh, name=sku, sku=sku,
            quantity=Decimal(qty), catalog_variant=v)
        return v

    def _run(self, apply=False):
        out = StringIO()
        with patch("operating.management.commands.merge_product_families.MERGES",
                   self.MERGES):
            call_command("merge_product_families", *(["--apply"] if apply else []),
                         stdout=out)
        return out.getvalue()

    def test_the_dry_run_writes_nothing(self):
        self._run()
        self.featured.refresh_from_db()
        self.assertEqual(self.featured.sku, "24592")
        self.assertEqual(Product.objects.count(), 2)
        self.moved.refresh_from_db()
        self.assertEqual(self.moved.product_id, self.hidden.pk)

    def test_the_featured_row_survives_and_takes_the_code(self):
        self._run(apply=True)
        self.featured.refresh_from_db()
        self.assertEqual(self.featured.title, "K24592")
        self.assertEqual(self.featured.sku, "K24592")
        self.assertTrue(self.featured.featured)
        self.assertFalse(Product.objects.filter(pk=self.hidden.pk).exists())
        self.assertEqual(Product.objects.count(), 1)

    def test_the_web_content_stays_put(self):
        self._run(apply=True)
        self.assertEqual(self.featured.files.count(), 1)

    def test_the_family_ends_up_under_one_product(self):
        self._run(apply=True)
        skus = set(self.featured.variants.values_list("variant_sku", flat=True))
        self.assertEqual(skus, {"K24592.G28", "K24592.G07"})

    def test_a_moved_variant_keeps_its_id_and_its_stock(self):
        """The variant moves house rather than being recreated, so warehouse
        rows and order lines pointing at it are undisturbed."""
        self._run(apply=True)
        self.moved.refresh_from_db()
        self.assertEqual(self.moved.product_id, self.featured.pk)
        self.assertEqual(self.moved.live_quantity, Decimal("102.30"))
        self.assertEqual(self.featured.live_quantity, Decimal("162.90"))

    def test_a_protected_order_line_is_moved_not_orphaned(self):
        """OrderItem.product is PROTECT: a single line left pointing at the
        husk would abort the delete outright."""
        order = Order.objects.create(order_number="DK-MERGE")
        OrderItem.objects.create(
            order=order, product=self.hidden, product_variant=self.moved,
            quantity=Decimal("5"), price=Decimal("1"))

        self._run(apply=True)

        self.assertFalse(Product.objects.filter(pk=self.hidden.pk).exists())
        line = OrderItem.objects.get()
        self.assertEqual(line.product_id, self.featured.pk)

    def test_running_it_twice_changes_nothing_more(self):
        self._run(apply=True)
        out = self._run(apply=True)
        self.assertIn("already merged", out)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(self.featured.variants.count(), 2)

    def test_it_reports_the_sku_it_is_taking_over(self):
        """The survivor's own old code is replaced — 2047 becomes Liva — so
        the dry run has to say so before anyone applies it."""
        out = self._run()
        self.assertIn("sku '24592' -> 'K24592'", out)
