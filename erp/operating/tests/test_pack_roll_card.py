# to run this test, use the command:
# python manage.py test operating.tests.test_pack_roll_card

"""Reading one roll off the packing screen.

While scanning a sack a packer sometimes realises a barcode was typed in
wrong — and by then the roll is already in a group or a package, past the
scanner. So every listed roll opens the same card a scan opens, and the
card leads on to the roll's own edit box.

Also pinned here: the figures the screen adds up are written unlocalized.
They used to go through floatformat, which in Turkish writes "13,00", and
every Number() over that was NaN — which is what package headers said.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from accounting.models import Book
from marketing.models import Product, ProductCategory
from operating.models import (Order, OrderItem, OrderStockReservation, Pack, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


class PackingScreenRolls(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(
            name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.order = Order.objects.create(order_number="DK0000301")
        self.pack = Pack.objects.create(order=self.order, pack_number=1)
        product = Product.objects.create(
            title="Bergamo", sku="BRG-01", price=10,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Bergamo", sku="BRG-01", quantity=Decimal("100.00"))
        self.item = OrderItem.objects.create(
            order=self.order, product=product, quantity=Decimal("100.00"), price=10)
        # 13 m cut off a 35 m roll — both figures are read by the JS.
        self.roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("35.00"),
            quantity_remaining=Decimal("35.00"), barcode="BC-301")
        self.reservation = OrderStockReservation.objects.create(
            order=self.order, order_item=self.item, stock_item=self.roll,
            warehouse_product=self.wp, quantity=Decimal("13.00"), pack=self.pack)
        self.client.force_login(User.objects.create_superuser("packer", "p@a.b", "pw"))

    def _html(self, lang="en"):
        with translation.override(lang):
            resp = self.client.get(
                reverse("operating:order_pack_scan", kwargs={"pk": self.order.pk}),
                headers={"accept-language": lang})
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_a_roll_carries_everything_its_card_shows(self):
        html = self._html()
        self.assertIn('data-barcode="BC-301"', html)
        self.assertIn('data-name="Bergamo"', html)
        self.assertIn('data-sku="BRG-01"', html)
        self.assertIn('data-warehouse="Fabrika"', html)

    def test_a_roll_links_to_its_own_edit_box(self):
        expected = "%s?roll=%s" % (
            reverse("operating:warehouse_product_detail",
                    kwargs={"warehouse_pk": self.wh.pk, "product_pk": self.wp.pk}),
            self.roll.pk)
        self.assertIn('data-roll-url="%s"' % expected, self._html())

    def test_the_figures_the_screen_adds_up_are_not_localized(self):
        """A Turkish "13,00" in a data attribute is NaN to Number() — which
        is what the package headers used to show."""
        html = self._html("tr")
        self.assertIn('data-quantity="13.00"', html)
        self.assertIn('data-remaining="35.00"', html)
        self.assertNotIn('data-quantity="13,00"', html)
        self.assertNotIn('data-remaining="35,00"', html)

    def test_a_turkish_reader_still_reads_a_turkish_number(self):
        """Only the machine-read attributes are unlocalized; the metres on
        the face of the row stay in the reader's own notation."""
        self.assertIn("13,00 m", self._html("tr"))
        self.assertIn("13.00 m", self._html("en"))

    def test_a_shipped_order_can_still_have_its_rolls_read(self):
        """Packing is locked once an order ships, but the rolls are exactly
        what someone comes back to check — so the card's shell is there
        even though nothing may be scanned into it."""
        self.order.order_status = "shipped"
        self.order.save(update_fields=["order_status"])
        html = self._html()
        self.assertIn('id="pkScanModal"', html)      # the card can still open
        self.assertIn('id="pkScanResult"', html)
        self.assertNotIn('id="pkVideo"', html)       # but there is no camera


class ArrivingOnOneRoll(TestCase):
    """?roll=<pk> on a product's page opens that roll's edit box, so the
    link the packing card hands over lands on the correction itself and
    not at the top of a list of hundreds."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(
            name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Bergamo", sku="BRG-01", quantity=Decimal("35.00"))
        self.roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("35.00"),
            quantity_remaining=Decimal("35.00"), barcode="BC-301")
        self.client.force_login(User.objects.create_superuser("wh", "w@a.b", "pw"))

    def test_the_page_knows_how_to_open_the_roll_it_was_sent_for(self):
        resp = self.client.get(reverse(
            "operating:warehouse_product_detail",
            kwargs={"warehouse_pk": self.wh.pk, "product_pk": self.wp.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('roll-row-%s' % self.roll.pk, html)   # the row to land on
        self.assertIn("get('roll')", html)                  # and the code that lands
