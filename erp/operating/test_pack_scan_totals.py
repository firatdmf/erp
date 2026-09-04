# to run this test, use the command:
# python manage.py test operating.test_pack_scan_totals

"""The packing screen's package headers: how many tops are in a sack and
how many metres they carry."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductCategory
from .models import (Order, OrderItem, OrderRollReservation, Pack, Warehouse,
                     WarehouseProduct, WarehouseProductRoll)


class PackHeaderTotals(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.order = Order.objects.create(order_number="DK0000292")
        self.pack1 = Pack.objects.create(order=self.order, pack_number=1)
        self.pack2 = Pack.objects.create(order=self.order, pack_number=2)

        self.item = self._tracked_item("Bergamo", "BRG-01")
        # Two tops in package 1, one of them cut down to 12.50 of its 40 m.
        self._reserve("BC1", Decimal("40.00"), Decimal("40.00"), self.pack1)
        self._reserve("BC2", Decimal("40.00"), Decimal("12.50"), self.pack1)
        # One top in package 2, and one scanned but not yet in any package.
        self._reserve("BC3", Decimal("25.00"), Decimal("25.00"), self.pack2)
        self._reserve("BC4", Decimal("18.00"), Decimal("18.00"), None)

        self.client.force_login(User.objects.create_superuser("packer", "p@a.b", "pw"))

    def _tracked_item(self, title, sku):
        """A line with warehouse stock behind it — the packing screen gives
        these the scan/pack UI."""
        product = Product.objects.create(
            title=title, sku=sku, price=10,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name=title, sku=sku, quantity=Decimal("100.00"))
        return OrderItem.objects.create(order=self.order, product=product,
                                        quantity=Decimal("100.00"), price=10)

    def _reserve(self, barcode, roll_meters, reserved, pack):
        roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=roll_meters, meters_remaining=roll_meters,
            barcode=barcode)
        return OrderRollReservation.objects.create(
            order=self.order, order_item=self.item, roll=roll,
            warehouse_product=self.wp, meters=reserved, pack=pack)

    def _packs(self):
        resp = self.client.get(reverse("operating:order_pack_scan",
                                       kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        return resp, {p.pack_number: p for p in resp.context["packs"]}

    def test_each_package_carries_its_own_tops_and_metres(self):
        _, packs = self._packs()
        self.assertEqual(packs[1].roll_count, 2)
        self.assertEqual(packs[1].total_meters, Decimal("52.50"))
        self.assertEqual(packs[2].roll_count, 1)
        self.assertEqual(packs[2].total_meters, Decimal("25.00"))

    def test_a_cut_top_counts_what_was_reserved_not_the_whole_roll(self):
        # BC2 is a 40 m roll cut to 12.50 for this order; the sack holds
        # 12.50, so that is what the header has to say.
        _, packs = self._packs()
        self.assertEqual(packs[1].total_meters, Decimal("52.50"))

    def test_an_unassigned_top_belongs_to_no_package(self):
        _, packs = self._packs()
        self.assertEqual(sum(p.roll_count for p in packs.values()), 3)
        self.assertEqual(sum(p.total_meters for p in packs.values()),
                         Decimal("77.50"))

    def test_an_untracked_line_is_counted_apart_from_the_metres(self):
        # A trade good with no warehouse entry: physically in the sack, but
        # its quantity is pieces — summing it into the metres would produce
        # a number that means nothing.
        trade = Product.objects.create(title="Kutu", sku="KUT-1", price=5)
        OrderItem.objects.create(order=self.order, product=trade,
                                 quantity=Decimal("3.00"), price=5,
                                 pack=self.pack2)
        _, packs = self._packs()
        self.assertEqual(packs[2].item_count, 1)
        self.assertEqual(packs[2].roll_count, 1)
        self.assertEqual(packs[2].total_meters, Decimal("25.00"))

    def test_an_empty_package_reads_zero(self):
        empty = Pack.objects.create(order=self.order, pack_number=3)
        _, packs = self._packs()
        self.assertEqual(packs[3].roll_count, 0)
        self.assertEqual(packs[3].total_meters, Decimal("0"))
        self.assertEqual(packs[3].item_count, 0)

    def test_the_header_prints_the_metres(self):
        resp, _ = self._packs()
        self.assertContains(resp, '<span data-meters>52.50</span> m', html=False)


class ReachingAPackageWithoutDragging(TestCase):
    """A roll must be able to reach a package without being dragged the
    length of a tall list — the packages get the full page width and
    their rolls flow across it, each package folds to one line, and
    every row carries a picker that names its destination outright."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.order = Order.objects.create(order_number="DK0000293")
        Pack.objects.create(order=self.order, pack_number=1)
        self.client.force_login(User.objects.create_superuser("p2", "p2@a.b", "pw"))

    def _html(self):
        resp = self.client.get(reverse("operating:order_pack_scan",
                                       kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_packing_gets_the_full_width_rather_than_half_of_it(self):
        self.assertIn("pk-grid-stack", self._html())

    def test_a_package_can_be_folded_down_to_its_header(self):
        html = self._html()
        self.assertIn("pk-pack-caret", html)      # the per-package fold control
        self.assertIn('id="pkCompactBtn"', html)  # and the fold-them-all button

    def test_a_row_can_pick_its_package_instead_of_being_dragged(self):
        html = self._html()
        self.assertIn("pk-menu-i", html)     # the package picker's entries
        self.assertIn("pk-move", html)       # the button that opens it

    def test_the_scanner_is_a_popup_reached_from_each_package(self):
        html = self._html()
        self.assertIn('id="pkScanModal"', html)   # one camera, in an overlay
        self.assertIn("pk-pack-scan", html)       # opened from a package header
        self.assertNotIn('id="pkCam"', html)      # no inline viewport left

    def test_packing_cannot_add_or_remove_a_roll(self):
        """The screen mirrors what the order holds: no barcode box to add
        with, and no delete button to drop one. Rolls are chosen on the
        order form; packing only decides which sack each goes in."""
        html = self._html()
        self.assertNotIn('id="pkManual"', html)     # the add box
        self.assertNotIn('id="pkOpenCam"', html)    # the card's camera button
        self.assertNotIn("pk-x", html)              # the delete-roll button
        self.assertNotIn("order_pack_reserve_remove", html)

    def test_the_list_is_named_for_what_the_order_makes_available(self):
        html = self._html()
        self.assertIn("Available rolls", html)
        self.assertNotIn("Scanned rolls", html)

    def test_packing_cannot_cut_a_roll(self):
        """Reserved metres are the invoiced quantity, so they are set on the
        order form — packing only reads them. The figure stays: it is the
        packer's instruction to cut 13 m off a 35 m roll."""
        html = self._html()
        self.assertNotIn("pk-scissors", html)
        self.assertNotIn("pk-cut-edit", html)
        self.assertNotIn("order_pack_reserve_update", html)
        self.assertIn("pk-cut-val", html)         # the metres are still shown

    def test_no_fixed_bar_sits_across_the_bottom_of_the_page(self):
        """It ran under the fixed sidebar, which painted over its text; the
        one action it carried (advancing the order to 'packaging') was
        dropped along with it."""
        html = self._html()
        self.assertNotIn("pk-foot", html)
        self.assertNotIn("pkComplete", html)


class ScanningStraightIntoAPackage(TestCase):
    """A packer works one sack at a time: arm a package, then every roll
    scanned goes into it, instead of landing loose and being dragged over
    afterwards."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.order = Order.objects.create(order_number="DK0000294")
        self.pack1 = Pack.objects.create(order=self.order, pack_number=1)
        self.pack2 = Pack.objects.create(order=self.order, pack_number=2)
        product = Product.objects.create(
            title="Bergamo", sku="BRG-01", price=10,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Bergamo", sku="BRG-01", quantity=Decimal("100.00"))
        self.item = OrderItem.objects.create(order=self.order, product=product,
                                             quantity=Decimal("100.00"), price=10)
        self.roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("40.00"),
            meters_remaining=Decimal("40.00"), barcode="SCAN-1")
        self.client.force_login(User.objects.create_superuser("p3", "p3@a.b", "pw"))
        self.url = reverse("operating:order_pack_reserve_add", kwargs={"pk": self.order.pk})

    def _scan(self, barcode="SCAN-1", **extra):
        return self.client.post(self.url, {"barcode": barcode, **extra},
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_a_scan_names_the_package_it_belongs_in(self):
        data = self._scan(pack_id=self.pack2.pk).json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["reservation"]["pack_id"], self.pack2.pk)
        self.assertEqual(OrderRollReservation.objects.get(roll=self.roll).pack_id, self.pack2.pk)

    def test_a_scan_with_no_package_still_lands_loose(self):
        data = self._scan().json()
        self.assertTrue(data["ok"])
        self.assertIsNone(data["reservation"]["pack_id"])

    def test_rescanning_a_held_roll_moves_it_into_the_armed_package(self):
        """The roll is in the packer's hand going into this sack — that is
        the only reading of a re-scan that matches what is happening."""
        self._scan(pack_id=self.pack1.pk)
        data = self._scan(pack_id=self.pack2.pk).json()
        self.assertTrue(data["duplicate"])
        self.assertTrue(data["moved"])
        self.assertEqual(OrderRollReservation.objects.get(roll=self.roll).pack_id, self.pack2.pk)
        self.assertEqual(OrderRollReservation.objects.filter(roll=self.roll).count(), 1)

    def test_rescanning_into_the_same_package_changes_nothing(self):
        self._scan(pack_id=self.pack1.pk)
        data = self._scan(pack_id=self.pack1.pk).json()
        self.assertTrue(data["duplicate"])
        self.assertFalse(data["moved"])

    def test_place_only_refuses_a_roll_the_order_does_not_hold(self):
        """The packing screen sends place_only, so a roll that is not on
        the order is turned away instead of quietly joining it — which
        would change what the order bills."""
        resp = self._scan(pack_id=self.pack1.pk, place_only="1")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["kind"], "not_in_order")
        self.assertFalse(OrderRollReservation.objects.filter(roll=self.roll).exists())

    def test_place_only_puts_a_held_roll_into_the_scanned_package(self):
        self._scan()                                    # the order takes it
        data = self._scan(pack_id=self.pack2.pk, place_only="1").json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["placed"])
        self.assertTrue(data["moved"])
        self.assertEqual(OrderRollReservation.objects.get(roll=self.roll).pack_id, self.pack2.pk)

    def test_place_only_leaves_a_roll_already_in_that_package_alone(self):
        self._scan(pack_id=self.pack2.pk)
        data = self._scan(pack_id=self.pack2.pk, place_only="1").json()
        self.assertTrue(data["placed"])
        self.assertFalse(data["moved"])
        self.assertEqual(OrderRollReservation.objects.filter(roll=self.roll).count(), 1)

    def test_a_preview_reports_the_roll_without_writing_anything(self):
        """The screen shows what it found and waits for a confirm, so the
        preview must be incapable of changing anything."""
        self._scan(pack_id=self.pack1.pk)                 # the order holds it, in #1
        data = self._scan(pack_id=self.pack2.pk, place_only="1", preview="1").json()
        self.assertTrue(data["preview"])
        self.assertTrue(data["held"])
        self.assertFalse(data["in_target"])               # not in #2 yet
        self.assertEqual(data["pack_number"], self.pack1.pack_number)
        self.assertEqual(data["reservation"]["barcode"], "SCAN-1")
        # Untouched: still in package 1, still exactly one reservation.
        self.assertEqual(OrderRollReservation.objects.get(roll=self.roll).pack_id, self.pack1.pk)
        self.assertEqual(OrderRollReservation.objects.count(), 1)

    def test_a_preview_knows_when_the_roll_is_already_in_that_package(self):
        self._scan(pack_id=self.pack2.pk)
        data = self._scan(pack_id=self.pack2.pk, place_only="1", preview="1").json()
        self.assertTrue(data["in_target"])

    def test_a_preview_refuses_a_roll_the_order_does_not_hold(self):
        resp = self._scan(pack_id=self.pack1.pk, place_only="1", preview="1")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["kind"], "not_in_order")
        self.assertFalse(OrderRollReservation.objects.exists())

    def test_a_package_from_another_order_is_refused(self):
        other = Pack.objects.create(order=Order.objects.create(order_number="DK0000295"),
                                    pack_number=1)
        resp = self._scan(pack_id=other.pk)
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(OrderRollReservation.objects.filter(roll=self.roll).exists())
