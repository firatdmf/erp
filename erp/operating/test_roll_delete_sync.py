# to run this test, use the command:
# python manage.py test operating.test_roll_delete_sync

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
        self.warehouse = Warehouse.objects.create(name="Fabrika")
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
