# to run this test, use the command:
# python manage.py test operating.test_roll_edit_reservations

"""Correcting a roll's length carries the orders holding it along.

A reservation keeps its OWN snapshot of the metres held, so shortening
the roll underneath it used to leave the order quoting a figure the roll
could no longer honour — and the warehouse blocking those metres from
everybody else until the discrepancy surfaced at ship time."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductCategory
from .models import (Order, OrderItem, OrderStockReservation, StockMovement,
                     Warehouse, WarehouseProduct, WarehouseProductItem)


class RollEditTrimsReservations(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(
            name="Laleli Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Bergamo", sku="BRG-01",
            quantity=Decimal("19.50"))
        self.roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("19.50"),
            quantity_remaining=Decimal("19.50"), barcode="2000039337908")

        self.user = User.objects.create_superuser("wh", "w@a.b", "pw")
        self.client.force_login(self.user)

    def _order(self, number, qty):
        product = Product.objects.create(
            title="Bergamo", sku=f"SKU-{number}", price=10,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        order = Order.objects.create(order_number=number, order_status="pending")
        item = OrderItem.objects.create(order=order, product=product,
                                        quantity=qty, price=10)
        res = OrderStockReservation.objects.create(
            order=order, order_item=item, stock_item=self.roll,
            warehouse_product=self.wp, quantity=qty)
        return order, res

    def _edit(self, meters):
        return self.client.post(
            reverse("operating:warehouse_roll_edit",
                    kwargs={"warehouse_pk": self.wh.pk,
                            "product_pk": self.wp.pk,
                            "roll_pk": self.roll.pk}),
            {"barcode": self.roll.barcode, "quantity": str(meters)},
        )

    def test_shortening_the_roll_trims_the_hold(self):
        """The reported case: 19.50 m held, roll re-measured at 18.50."""
        order, res = self._order("DK0000297", Decimal("19.50"))

        resp = self._edit("18.50")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])

        res.refresh_from_db()
        self.assertEqual(res.quantity, Decimal("18.50"))
        # ...and the user is told, rather than finding out at ship time.
        self.assertEqual(len(body["reservations_trimmed"]), 1)
        self.assertEqual(body["reservations_trimmed"][0]["was"], 19.50)
        self.assertEqual(body["reservations_trimmed"][0]["now"], 18.50)

    def test_a_hold_that_still_fits_is_left_alone(self):
        order, res = self._order("DK0000298", Decimal("12.00"))

        body = self._edit("18.50").json()

        res.refresh_from_db()
        self.assertEqual(res.quantity, Decimal("12.00"))
        self.assertEqual(body["reservations_trimmed"], [])

    def test_a_longer_roll_does_not_grow_the_hold(self):
        """The order asked for a quantity, not for whatever the roll carries."""
        order, res = self._order("DK0000299", Decimal("19.50"))

        self._edit("25.00")

        res.refresh_from_db()
        self.assertEqual(res.quantity, Decimal("19.50"))

    def test_oldest_hold_keeps_its_claim(self):
        """Two orders on one roll: the shortfall lands on the later picker."""
        first, res_first = self._order("DK0000300", Decimal("12.00"))
        second, res_second = self._order("DK0000301", Decimal("7.50"))

        body = self._edit("15.00").json()

        res_first.refresh_from_db()
        res_second.refresh_from_db()
        self.assertEqual(res_first.quantity, Decimal("12.00"))
        self.assertEqual(res_second.quantity, Decimal("3.00"))
        self.assertEqual(len(body["reservations_trimmed"]), 1)

    def test_a_hold_left_with_nothing_is_released(self):
        """An empty reservation is a roll on a packing list carrying zero."""
        first, res_first = self._order("DK0000302", Decimal("15.00"))
        second, res_second = self._order("DK0000303", Decimal("4.50"))

        self._edit("15.00")

        res_first.refresh_from_db()
        self.assertEqual(res_first.quantity, Decimal("15.00"))
        self.assertFalse(
            OrderStockReservation.objects.filter(pk=res_second.pk).exists())

    def test_the_trim_leaves_a_trace_on_the_roll(self):
        """The order's figure changing on its own needs a visible cause."""
        order, res = self._order("DK0000304", Decimal("19.50"))

        self._edit("18.50")

        moves = StockMovement.objects.filter(
            stock_item=self.roll, movement_type="adjustment",
            reason__startswith="Reservation trimmed")
        self.assertEqual(moves.count(), 1)
        self.assertEqual(moves.first().quantity, Decimal("1.00"))

    def test_shipped_metres_still_refuse_the_edit(self):
        """Unchanged: outgoing history is a fact, not a soft hold."""
        self.roll.quantity_remaining = Decimal("7.50")   # 12.00 already gone
        self.roll.save(update_fields=["quantity_remaining"])

        resp = self._edit("10.00")

        self.assertEqual(resp.status_code, 400)
        self.roll.refresh_from_db()
        self.assertEqual(self.roll.quantity, Decimal("19.50"))
