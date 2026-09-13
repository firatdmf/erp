"""The create form and the view have to agree on ONE name for the
metres/units a picked stock item contributes.

Commit 4ebbc868 renamed the warehouse's `meters` columns to `quantity`
with a blanket search-and-replace that also swept the order form's
CLIENT-SIDE roll objects — but only their readers. The three places that
BUILT a roll object went on writing `meters`, so every freshly picked
stock item read back as `undefined`: the line's quantity summed to zero,
the form refused to save with "… için henüz top seçilmedi", and the
payload posted `quantity: undefined`, which the view read as "no cut
asked for" and reserved the whole stock item regardless of the scissors.

Run with:
    python manage.py test operating.test_order_roll_payload_key
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product

from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                     WarehouseProductItem)

SKU = "KZL000315"


class RollPayloadKey(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        self.product = Product.objects.create(title="Crepe", sku=SKU, price=10)
        wh = Warehouse.objects.create(name="Laleli depo", accounting_book=book)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Crepe", sku=SKU, quantity=Decimal("50"))
        self.roll = WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode="20582310112", status="in_stock")

        User = get_user_model()
        user = User.objects.create_superuser("seller", "s@t.com", "pw")
        user.member.books.add(book)
        user.member.default_book = book
        user.member.save()
        self.client.force_login(user)

    def _place(self, rolls, quantity):
        resp = self.client.post(reverse("operating:create_order"), {
            "customer_type": "retail",
            "retail_customer_name": "Walk-in",
            "product_json_input": json.dumps([{
                "item_no": 1,
                "product": {"sku": SKU, "variant": False},
                "description": "",
                "quantity": quantity,
                "outsourced": 0,
                "price": 2,
                "is_custom_curtain": False,
                "rolls": rolls,
            }]),
        })
        self.assertIn(resp.status_code, (200, 302))
        return Order.objects.latest("pk")

    def test_a_whole_stock_item_is_reserved_in_full(self):
        order = self._place(
            [{"barcode": "20582310112", "quantity": 50}], quantity=50)
        res = OrderStockReservation.objects.get(order=order)
        self.assertEqual(res.quantity, Decimal("50.00"))

    def test_the_scissors_cut_survives_the_post(self):
        """A partial cut travels under the key the view reads. Posted
        under any OTHER name the view sees no request at all and hands
        back the whole 50 m stock item."""
        order = self._place(
            [{"barcode": "20582310112", "quantity": 28.5}], quantity=28.5)
        res = OrderStockReservation.objects.get(order=order)
        self.assertEqual(res.quantity, Decimal("28.50"))

    def test_the_form_builds_its_roll_objects_under_that_same_key(self):
        """Guards the client half: every site that pushes a roll onto a
        line has to write `quantity`, because syncQtyFromRolls — the
        function that turns picked stock items into the line's quantity —
        reads `quantity` and nothing else."""
        with open("operating/templates/operating/partials/"
                  "create_order_form.html", encoding="utf-8") as fh:
            form = fh.read()
        self.assertNotIn("meters: known.available", form)
        self.assertNotIn("meters: d.available", form)
        self.assertIn("quantity: known.available", form)
        self.assertIn("quantity: d.available", form)
        # The submitted roll names its metres `quantity` too. Matched on
        # the pair rather than one exact line: the payload has since grown
        # the roll's book alongside it, and this test is about the NAME,
        # not about what else travels with it.
        import re
        submitted = re.search(r"rolls: \(it\.rolls \|\| \[\]\)\.map\((.{0,220})", form, re.S)
        self.assertIsNotNone(submitted, "the submitted rolls map moved")
        self.assertIn("quantity: r.quantity", submitted.group(1))
        self.assertNotIn("meters: r.quantity", submitted.group(1))
