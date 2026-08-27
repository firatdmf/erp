# to run this test, use the command:
# python manage.py test operating.test_label_quantity

import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from operating.models import Warehouse, WarehouseProduct, WarehouseProductRoll


class LabelShowsRemainingMetersTest(TestCase):
    """A roll that's been cut carries its leftover in meters_remaining;
    `meters` stays the length it arrived at. The label printed the arrival
    length, so KAR0001468 kept reprinting 18.50 after being cut down to
    12.90 — the sticker contradicted the shelf it was stuck to.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="label_tester", password="pw", email="l@a.b")
        self.client.force_login(self.user)
        self.warehouse = Warehouse.objects.create(name="Fabrika")
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="KARDELEN", sku="KAR0001468",
            quantity=Decimal("12.90"))
        # reportlab flate-compresses page streams by default, which would
        # hide the drawn strings from a byte search. Off for the test only.
        import reportlab.rl_config as rl_config
        self._compression = rl_config.pageCompression
        rl_config.pageCompression = 0
        self.addCleanup(setattr, rl_config, "pageCompression", self._compression)

    def _drawn_strings(self, roll):
        url = reverse("operating:warehouse_product_label", kwargs={
            "warehouse_pk": self.warehouse.pk, "product_pk": self.wp.pk})
        resp = self.client.get(url, {"roll": roll.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        # Every string the canvas draws lands in the page stream as "(text) Tj".
        return [s.decode("latin-1") for s in re.findall(rb"\((.*?)\)\s*Tj", resp.content)]

    def test_cut_roll_prints_what_is_left(self):
        roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("18.50"),
            meters_remaining=Decimal("12.90"), status="partial",
            barcode="KAR0001468")
        drawn = self._drawn_strings(roll)
        self.assertIn("12.90", drawn)
        self.assertNotIn("18.50", drawn)

    def test_uncut_roll_still_prints_its_full_length(self):
        # meters_remaining is null until the first cut — the label has to
        # fall back to meters there rather than printing 0.00.
        roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("18.50"), barcode="KAR0001469")
        self.assertIn("18.50", self._drawn_strings(roll))

    def test_fully_consumed_roll_prints_zero(self):
        # A consumed roll only prints when asked for by pk; it should say
        # it's empty rather than advertise the length it once had.
        roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("18.50"),
            meters_remaining=Decimal("0.00"), status="consumed",
            barcode="KAR0001470")
        drawn = self._drawn_strings(roll)
        self.assertIn("0.00", drawn)
        self.assertNotIn("18.50", drawn)
