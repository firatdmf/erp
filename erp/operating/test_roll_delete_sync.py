# to run this test, use the command:
# python manage.py test operating.test_roll_delete_sync

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

import json

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from marketing.models import Product, ProductVariant
from operating.models import (
    StockMovement, Warehouse, WarehouseProduct, WarehouseProductRoll,
)


class RollDeleteKeepsCatalogInStepTest(TestCase):
    """Deleting a roll drops the warehouse quantity — the catalog variant
    mirrors that quantity, so it has to come down too. It didn't, which is
    why N1464T.G54 still read 33.66 in the intake chips after its only roll
    was deleted.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="roll_tester", password="pw", email="r@o.l")
        self.client.force_login(self.user)
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        product = Product.objects.create(title="N1464T", sku="N1464T", featured=False)
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="N1464T.G54", variant_quantity=Decimal("33.66"))
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="MARLETTOO", sku="N1464T.G54",
            quantity=Decimal("33.66"), catalog_variant=self.variant)
        self.roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("33.66"), barcode="2000043130007")

    def _delete(self, roll):
        return self.client.post(
            reverse("operating:warehouse_roll_delete",
                    args=[self.warehouse.pk, self.wp.pk, roll.pk]),
            {"reason": "Roll deleted"},
            headers={"x-requested-with": "XMLHttpRequest"})

    def test_both_sides_come_down_together(self):
        r = self._delete(self.roll)
        self.assertEqual(r.status_code, 200, r.content)
        self.wp.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.wp.quantity, Decimal("0.00"))
        self.assertEqual(self.variant.variant_quantity, Decimal("0.00"))

    def test_it_is_still_a_correction_not_a_sale(self):
        """The distinction is deliberate: real stock-out happens when an
        order ships, so a deleted roll must never inflate Stock out."""
        self._delete(self.roll)
        kinds = list(StockMovement.objects.filter(product=self.wp)
                     .values_list("movement_type", flat=True))
        self.assertIn("adjustment", kinds)
        self.assertNotIn("out", kinds)

    def test_the_stats_row_reconciles(self):
        """in − out + corrections = current stock, so the page can explain
        itself after a deletion."""
        StockMovement.objects.create(
            product=self.wp, movement_type="in", quantity=Decimal("33.66"),
            reason="Roll scanned")
        self._delete(self.roll)
        r = self.client.get(reverse("operating:warehouse_product_detail",
                                    args=[self.warehouse.pk, self.wp.pk]))
        ctx = r.context
        self.assertEqual(ctx["in_total"], Decimal("33.66"))
        self.assertEqual(ctx["out_total"], Decimal("0"))
        self.assertEqual(ctx["adjust_total"], Decimal("-33.66"))
        self.wp.refresh_from_db()
        self.assertEqual(
            ctx["in_total"] - ctx["out_total"] + ctx["adjust_total"], self.wp.quantity)


class ProductBarcodeIsNotStampedFromRollsTest(TestCase):
    """A barcode identifies one physical top, so it never lands on the parent.

    Intake used to copy the first roll's code onto WarehouseProduct.barcode.
    That made the product advertise a code belonging to a single roll, and
    _barcode_taken() checks products as well as rolls — so once the roll was
    deleted the code stayed reserved against something that no longer
    existed, and re-entering the same top was refused as a duplicate.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="bc_tester", password="pw", email="b@c.t")
        self.client.force_login(self.user)
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd)

    def _receive(self, barcode, main=None):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "cari_id": self.cari.pk, "unit": "mt",
                "products": [{
                    "main_product": main or {"mode": "new", "name": "K24644", "sku": "K24644"},
                    "has_variants": True,
                    "variants": [{"name": "G07", "sku": "K24644.G07", "price": "1",
                                  "currency": "USD",
                                  "tops": [{"qty": 33.66, "barcode": barcode}]}],
                }],
            }), content_type="application/json")

    def test_receiving_leaves_the_product_barcode_empty(self):
        self.assertEqual(self._receive("2000043130007").status_code, 200)
        wp = WarehouseProduct.objects.get(sku="K24644.G07")
        self.assertIsNone(wp.barcode)
        self.assertEqual(wp.rolls.get().barcode, "2000043130007")

    def test_the_code_is_reusable_once_its_roll_is_deleted(self):
        from operating.views_warehouse import _barcode_taken
        self._receive("2000043130007")
        wp = WarehouseProduct.objects.get(sku="K24644.G07")
        roll = wp.rolls.get()
        self.assertTrue(_barcode_taken("2000043130007"))   # the roll holds it

        r = self.client.post(
            reverse("operating:warehouse_roll_delete",
                    args=[self.warehouse.pk, wp.pk, roll.pk]),
            {"reason": "Roll deleted"}, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(_barcode_taken("2000043130007"))

        # ...and the same top can be entered again, which is the whole point.
        # (Against the EXISTING product — its main SKU is taken now, as it
        # should be; only the barcode had to be released.)
        existing = Product.objects.get(sku="K24644")
        again = self._receive("2000043130007",
                              main={"mode": "existing", "id": existing.pk})
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(
            WarehouseProductRoll.objects.filter(barcode="2000043130007").count(), 1)

    def test_a_hand_entered_product_barcode_survives_roll_changes(self):
        """The field is now only ever set deliberately, so nothing may wipe
        it — the old cleanup helper would have, on the next roll change."""
        self._receive("2000043130007")
        wp = WarehouseProduct.objects.get(sku="K24644.G07")
        wp.barcode = "ARTICLE-8690000"
        wp.save(update_fields=["barcode"])

        roll = wp.rolls.get()
        self.client.post(
            reverse("operating:warehouse_roll_delete",
                    args=[self.warehouse.pk, wp.pk, roll.pk]),
            {"reason": "Roll deleted"}, headers={"x-requested-with": "XMLHttpRequest"})
        wp.refresh_from_db()
        self.assertEqual(wp.barcode, "ARTICLE-8690000")
