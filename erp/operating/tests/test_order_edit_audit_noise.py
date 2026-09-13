# to run this test, use the command:
# python manage.py test operating.test_order_edit_audit_noise

"""Re-saving an order that changed nothing records nothing.

The save paths used to assign the raw JSON number to quantity and price,
which are DecimalFields. A float assigned to one stays a float on the
instance, and the audit signal compares the database's Decimal('66.40')
with the instance's 66.4 — unequal in Python — so every save of every
line wrote "quantity 66.40 -> 66.4". By September that was 223 of the 274
quantity/price rows in the change history: a record of changes that never
happened, burying the ones that did.
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

from operating.models import (Order, OrderChange, Warehouse, WarehouseProduct,
                     WarehouseProductItem)

SKU = "K24644.G07"


class OrderEditAuditNoise(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Anna Lugansk")

        product, _ = Product.objects.get_or_create(
            sku=SKU.split(".")[0], defaults={"title": "Krep"})
        ProductVariant.objects.get_or_create(product=product, variant_sku=SKU)
        wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("66.40"))
        WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("66.40"),
            quantity_remaining=Decimal("66.40"), barcode="L-0001",
            status="in_stock")

        User = get_user_model()
        self.user = User.objects.create_superuser("seller", "s@t.com", "pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        self.client.force_login(self.user)

    def _line(self, item_id=None, qty=66.4, price=3.6, rolls=True):
        line = {
            "item_no": 1,
            "product": {"sku": SKU, "variant": True},
            "description": "", "quantity": qty, "outsourced": 0,
            "price": price, "is_custom_curtain": False,
            "rolls": [{"barcode": "L-0001", "quantity": qty}] if rolls else [],
        }
        if item_id:
            line["item_id"] = item_id
        return line

    def _form(self, lines):
        return {
            "customer_type": "contact",
            "customer_pk": self.customer.pk,
            "book": self.book.pk,
            "product_json_input": json.dumps(lines),
        }

    def _create(self):
        self.client.post(reverse("operating:create_order"),
                         self._form([self._line()]))
        return Order.objects.get()

    def _edit(self, order, **line):
        item = order.items.get()
        return self.client.post(
            reverse("operating:edit_order", kwargs={"pk": order.pk}),
            self._form([self._line(item_id=item.pk, **line)]))

    def _figure_changes(self, order):
        return OrderChange.objects.filter(
            order=order, action="item_updated", field__in=["quantity", "price"])

    def test_resaving_an_unchanged_order_logs_nothing(self):
        """The reported symptom: "66.40 -> 66.4" and "3.60 -> 3.6"."""
        order = self._create()

        self._edit(order)

        self.assertEqual(
            list(self._figure_changes(order).values_list(
                "field", "old_value", "new_value")),
            [])

    def test_saving_twice_still_logs_nothing(self):
        order = self._create()
        self._edit(order)
        self._edit(order)
        self.assertEqual(self._figure_changes(order).count(), 0)

    def test_a_real_price_change_is_still_recorded(self):
        """Silencing the noise must not silence the signal."""
        order = self._create()

        self._edit(order, price=4.25)

        rows = list(self._figure_changes(order).values_list(
            "field", "old_value", "new_value"))
        self.assertEqual(rows, [("price", "3.60", "4.25")])

    def test_a_hand_typed_line_without_rolls_logs_nothing_on_resave(self):
        """Untracked lines take the same assignment path.

        The figures matter: 75 and 2.5 are exact in binary, so Decimal
        and float agree on them and the bug never shows. 75.3 and 2.7 are
        not, which is the ordinary case for metres and prices."""
        self.client.post(reverse("operating:create_order"), self._form([
            self._line(qty=75.3, price=2.7, rolls=False) | {"outsourced": 75.3}]))
        order = Order.objects.get()
        item = order.items.get()

        self.client.post(
            reverse("operating:edit_order", kwargs={"pk": order.pk}),
            self._form([self._line(item_id=item.pk, qty=75.3, price=2.7,
                                   rolls=False) | {"outsourced": 75.3}]))

        self.assertEqual(self._figure_changes(order).count(), 0)

    def test_stored_figures_are_exact(self):
        order = self._create()
        self._edit(order)
        item = order.items.get()
        self.assertEqual(item.quantity, Decimal("66.40"))
        self.assertEqual(item.price, Decimal("3.60"))
