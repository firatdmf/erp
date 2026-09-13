# to run this test, use the command:
# python manage.py test operating.test_line_matches_reservations

"""A saved line quotes the metres actually held for it, not the metres
the form hoped for.

The browser works out a line's quantity from the rolls it believes are
free; the server reserves each one against what the database really has
at that instant. Between the page loading and the save landing, someone
else can take the metres, the roll can be re-measured, or the barcode can
stop resolving — and every one of those used to leave the line quoting
the browser's figure while holding less.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from crm.models import Contact
from marketing.models import Product, ProductVariant

from operating.models import (Order, OrderStockReservation, Warehouse,
                     WarehouseProduct, WarehouseProductItem)

SKU = "K24644.G07"


class LineMatchesItsReservations(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Oleg Motuzenko")

        product, _ = Product.objects.get_or_create(
            sku=SKU.split(".")[0], defaults={"title": "Krep"})
        self.variant, _ = ProductVariant.objects.get_or_create(
            product=product, variant_sku=SKU)
        wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
            catalog_variant=self.variant)
        self.roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("50"),
            quantity_remaining=Decimal("50"), barcode="L-0001", status="in_stock")

        User = get_user_model()
        self.user = User.objects.create_superuser("seller", "s@t.com", "pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.client.force_login(self.user)

    def _post(self, lines):
        return self.client.post(reverse("operating:create_order"), {
            "customer_type": "contact",
            "customer_pk": self.customer.pk,
            "book": self.book.pk,
            "product_json_input": json.dumps(lines),
        })

    def _line(self, qty, roll_qty, barcode="L-0001", outsourced=0):
        return {
            "item_no": 1,
            "product": {"sku": SKU, "variant": True},
            "description": "", "quantity": qty, "outsourced": outsourced,
            "price": 2, "is_custom_curtain": False,
            "rolls": [{"barcode": barcode, "quantity": roll_qty}],
        }

    def _held(self, item):
        return sum((r.quantity or Decimal("0"))
                   for r in OrderStockReservation.objects.filter(order_item=item))

    # ── the case this exists for ────────────────────────────────────
    def test_a_competing_hold_pulls_the_line_down(self):
        """Someone else took 20 m between the form loading and saving."""
        rival = Order.objects.create(order_number="RIVAL")
        OrderStockReservation.objects.create(
            order=rival, stock_item=self.roll, warehouse_product=self.wp,
            quantity=Decimal("20.00"))

        self._post([self._line(qty=50, roll_qty=50)])

        item = Order.objects.exclude(pk=rival.pk).get().items.get()
        self.assertEqual(self._held(item), Decimal("30.00"))
        self.assertEqual(item.quantity, Decimal("30.00"))

    def test_a_roll_re_measured_mid_form_pulls_the_line_down(self):
        self.roll.quantity_remaining = Decimal("42.00")
        self.roll.save(update_fields=["quantity_remaining"])

        self._post([self._line(qty=50, roll_qty=50)])

        item = Order.objects.get().items.get()
        self.assertEqual(item.quantity, Decimal("42.00"))
        self.assertEqual(self._held(item), Decimal("42.00"))

    def test_the_user_is_told_the_line_shrank(self):
        rival = Order.objects.create(order_number="RIVAL")
        OrderStockReservation.objects.create(
            order=rival, stock_item=self.roll, warehouse_product=self.wp,
            quantity=Decimal("20.00"))

        resp = self._post([self._line(qty=50, roll_qty=50)])

        notes = [str(m) for m in resp.wsgi_request._messages]
        self.assertTrue(any("reduced to what is actually held" in n
                            for n in notes), notes)

    # ── what must NOT move ──────────────────────────────────────────
    def test_a_fully_reservable_line_is_left_exactly_as_picked(self):
        self._post([self._line(qty=50, roll_qty=50)])

        item = Order.objects.get().items.get()
        self.assertEqual(item.quantity, Decimal("50.00"))

    def test_outsourced_metres_are_kept_on_top(self):
        """quantity = what is held + what is coming from elsewhere."""
        self.roll.quantity_remaining = Decimal("42.00")
        self.roll.save(update_fields=["quantity_remaining"])

        self._post([self._line(qty=60, roll_qty=50, outsourced=10)])

        item = Order.objects.get().items.get()
        self.assertEqual(item.outsourced_quantity, Decimal("10.00"))
        self.assertEqual(item.quantity, Decimal("52.00"))   # 42 held + 10

    def test_an_unchanged_line_reports_nothing(self):
        """The save paths assign the raw JSON number to a Decimal field, so
        quantity arrives here as a float. Decimal('96.20') != 96.2 in
        Python, which made every ordinary line claim it had moved and
        report "96.20 -> 96.20" at the user."""
        from operating.views import _sync_line_to_reservations
        self._post([self._line(qty=50, roll_qty=50)])
        item = Order.objects.get().items.get()

        item.quantity = 50.0                       # float, as a save leaves it
        self.assertIsNone(_sync_line_to_reservations(item))

        item.quantity = float(Decimal("50.00"))
        self.assertIsNone(_sync_line_to_reservations(item))

    def test_editing_an_order_warns_about_nothing(self):
        """The whole-order case: re-saving an edit form that changed no
        metres must not produce a single 'reduced' line."""
        self._post([self._line(qty=50, roll_qty=50)])
        order = Order.objects.get()

        resp = self.client.post(
            reverse("operating:edit_order", kwargs={"pk": order.pk}), {
                "customer_type": "contact",
                "customer_pk": self.customer.pk,
                "book": self.book.pk,
                "product_json_input": json.dumps([{
                    "item_no": 1, "item_id": order.items.get().pk,
                    "product": {"sku": SKU, "variant": True},
                    "description": "", "quantity": 50, "outsourced": 0,
                    "price": 2, "is_custom_curtain": False,
                    "rolls": [{"barcode": "L-0001", "quantity": 50}],
                }]),
            })

        notes = [str(m) for m in resp.wsgi_request._messages]
        self.assertFalse(any("reduced to what is actually held" in n
                             for n in notes), notes)
        self.assertEqual(Order.objects.get().items.get().quantity,
                         Decimal("50.00"))

    def test_a_line_with_no_rolls_keeps_its_typed_quantity(self):
        """An untracked product, a back-order or a legacy row. Reading it
        off reservations there would mean zeroing it."""
        self._post([{
            "item_no": 1,
            "product": {"sku": SKU, "variant": True},
            "description": "", "quantity": 75, "outsourced": 75, "price": 2,
            "is_custom_curtain": False, "rolls": [],
        }])

        item = Order.objects.get().items.get()
        self.assertEqual(item.quantity, Decimal("75.00"))
        self.assertEqual(self._held(item), Decimal("0"))

    def test_a_line_whose_barcode_failed_is_not_silently_zeroed(self):
        """Nothing reserved at all is loud already (failed_barcodes); wiping
        the line on top of that would hide what was asked for."""
        self._post([self._line(qty=50, roll_qty=50, barcode="NOPE")])

        item = Order.objects.get().items.get()
        self.assertEqual(self._held(item), Decimal("0"))
        self.assertEqual(item.quantity, Decimal("50.00"))
