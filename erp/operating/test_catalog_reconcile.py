# to run this test, use the command:
# python manage.py test operating.test_catalog_reconcile

from decimal import Decimal
from unittest.mock import patch

from django.db import connection

from django.test import TestCase

from accounting.models import Book
from marketing.models import Product, ProductVariant
from operating.catalog_reconcile import reconcile_all_warehouse_links
from operating.models import Warehouse, WarehouseProduct


class DryRunPredictsTheApplyRunTest(TestCase):
    """A dry run is only worth running if its numbers are the numbers you
    get from --apply. Two of them weren't.

    Seven sibling SKUs of one base (K12504.G07, .G28, .G47, ...) need ONE
    hidden parent between them, and that is what apply creates — but the
    preview created nothing, so its "would create a parent" bookkeeping
    never filled in and it counted a seventh product seven times. On the
    real warehouse that read 673 new products where 379 were coming.

    And `relinked_wps` — how many warehouse rows actually change hands,
    the single number the preview exists to show — was only incremented
    inside the `if apply` branch, so every dry run reported zero.
    """

    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name="Ergene Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        for colour in ("G07", "G28", "G47", "G50", "G52", "G56", "G68"):
            WarehouseProduct.objects.create(
                warehouse=self.warehouse, name=f"KAREN {colour}",
                sku=f"K12504.{colour}", quantity=Decimal("10.00"))

    def test_preview_counts_one_parent_for_a_family_of_siblings(self):
        preview = reconcile_all_warehouse_links(apply=False)
        self.assertEqual(preview["products_created"], 1)
        self.assertEqual(preview["variants_created"], 7)

    def test_preview_counts_the_rows_that_will_change_hands(self):
        preview = reconcile_all_warehouse_links(apply=False)
        self.assertEqual(preview["relinked_wps"], 7)

    def test_the_preview_wrote_nothing(self):
        reconcile_all_warehouse_links(apply=False)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(ProductVariant.objects.count(), 0)
        self.assertFalse(
            WarehouseProduct.objects.exclude(catalog_variant=None).exists())

    def test_apply_produces_exactly_what_the_preview_promised(self):
        preview = reconcile_all_warehouse_links(apply=False)
        applied = reconcile_all_warehouse_links(apply=True)

        for key in ("groups", "linked_wps", "relinked_wps",
                    "variants_created", "variants_moved", "products_created"):
            self.assertEqual(preview[key], applied[key], key)

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ProductVariant.objects.count(), 7)
        parent = Product.objects.get()
        self.assertEqual(parent.title, "K12504")
        self.assertFalse(parent.featured, "auto-created parents stay off the site")
        # Stock is not copied anywhere: linking the seven warehouse rows IS
        # the product's 7 x 10.00 metres.
        self.assertEqual(parent.live_quantity, Decimal("70.00"))
        self.assertFalse(
            WarehouseProduct.objects.filter(catalog_variant=None).exists())

    def test_a_second_apply_is_a_no_op(self):
        reconcile_all_warehouse_links(apply=True)
        again = reconcile_all_warehouse_links(apply=True)
        self.assertEqual(again["products_created"], 0)
        self.assertEqual(again["variants_created"], 0)
        self.assertEqual(again["relinked_wps"], 0)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ProductVariant.objects.count(), 7)


class OneBadSkuDoesNotSinkTheRunTest(TestCase):
    """Every group used to share the caller's transaction. A DB-level error
    on one SKU left that transaction unusable, so every group after it died
    on TransactionManagementError: one real conflict became a wall of fake
    ones, and nothing after the bad row got linked at all.

    Each group now runs in its own savepoint, so the damage stops there.
    The failure is injected as a genuine failing statement rather than a
    bare raise, because it is the *database's* view of the transaction —
    not the Python exception — that used to take the rest of the run down.
    """

    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name="Ergene Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        # Groups are walked in sorted SKU order, so "AAA..." fails first and
        # the "ZZZ..." pair is everything that comes after it.
        WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="CLASH", sku="AAA.G01",
            quantity=Decimal("5.00"))
        for colour in ("G07", "G28"):
            WarehouseProduct.objects.create(
                warehouse=self.warehouse, name=f"KAREN {colour}",
                sku=f"ZZZ.{colour}", quantity=Decimal("10.00"))

    def _reconcile_with_one_bad_sku(self):
        real_create = ProductVariant.objects.create

        def flaky_create(**kwargs):
            if (kwargs.get("variant_sku") or "").startswith("AAA"):
                with connection.cursor() as cur:
                    cur.execute("SELECT 1 / 0")
            return real_create(**kwargs)

        with patch.object(ProductVariant.objects, "create", flaky_create):
            return reconcile_all_warehouse_links(apply=True)

    def test_the_healthy_skus_after_it_are_still_linked(self):
        s = self._reconcile_with_one_bad_sku()
        self.assertEqual(len(s["conflicts"]), 1, s["conflicts"])
        self.assertEqual(s["conflicts"][0]["sku"], "AAA.G01")

        linked = WarehouseProduct.objects.filter(sku__startswith="ZZZ")
        self.assertEqual(linked.count(), 2)
        for wp in linked:
            self.assertIsNotNone(wp.catalog_variant, f"{wp.sku} was left unlinked")

    def test_the_failed_group_leaves_no_half_written_rows(self):
        self._reconcile_with_one_bad_sku()
        self.assertFalse(
            Product.objects.filter(title="AAA").exists(),
            "the parent created before the failing statement should roll back")
        self.assertIsNone(
            WarehouseProduct.objects.get(sku="AAA.G01").catalog_variant)

    def test_counters_do_not_credit_the_failed_group(self):
        s = self._reconcile_with_one_bad_sku()
        # ZZZ.G07 and ZZZ.G28 only: one parent, two variants.
        self.assertEqual(s["products_created"], 1)
        self.assertEqual(s["variants_created"], 2)
        self.assertEqual(s["relinked_wps"], 2)
