"""The picking list names the rolls the order print only counts: under the
warehouse each stands in, by barcode and lot, whole roll or cut — with no
prices and no customer name, and the lines still short listed at the end.

Run with:
    python manage.py test operating.tests.test_order_picking_list
"""
import html
import re
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import (Order, OrderItem, OrderStockReservation, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


class OrderPickingListTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Anna Secretname")
        self.product = Product.objects.create(title="Krep", sku="KRP")
        self.user = get_user_model().objects.create_user("staff_picking", password="pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _order(self, book, number, **kw):
        account, _ = CurrentAccount.objects.get_or_create(
            book=book, contact=self.customer,
            defaults={"code": f"C-{book.pk}", "name": "Anna Secretname", "type": "customer",
                      "default_currency": self.usd})
        return Order.objects.create(order_number=number, current_account=account,
                                    contact=self.customer, **kw)

    def _line(self, order, qty, price="7.77", variant=None):
        return OrderItem.objects.create(order=order, product=self.product, product_variant=variant,
                                        quantity=Decimal(qty), price=Decimal(price))

    def _hold(self, line, barcode, take, warehouse, book, on_roll=None, lot="L1"):
        wh, _ = Warehouse.objects.get_or_create(name=warehouse, accounting_book=book)
        wp, _ = WarehouseProduct.objects.get_or_create(warehouse=wh, sku="KRP", defaults={"name": "Krep"})
        on_roll = Decimal(on_roll or take)
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=on_roll, quantity_remaining=on_roll,
            barcode=barcode, lot_number=lot, status="in_stock")
        OrderStockReservation.objects.create(order=line.order, order_item=line, stock_item=roll,
                                             warehouse_product=wp, quantity=Decimal(take))

    def _page(self, order):
        response = self.client.get(reverse("operating:order_picking_list", args=[order.pk]),
                                   {"html": "1"})
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _rows(self, body):
        body = body[body.index("<tbody>"):body.index("</tbody>")]
        return [(cls, re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip())
                for cls, inner in re.findall(r'<tr(?: class="([^"]*)")?>(.*?)</tr>', body, re.S)]

    def test_rolls_are_named_under_their_warehouse(self):
        order = self._order(self.laleli, "ORD-1")
        line = self._line(order, "30")
        self._hold(line, "R-100", "20", "Laleli", self.laleli, lot="7")
        self._hold(line, "R-200", "10", "Laleli Fabrika", self.laleli, on_roll="45")

        rows = self._rows(self._page(order))
        self.assertEqual([cls for cls, _ in rows], ["wh", "pr", "", "wh", "pr", ""])
        self.assertTrue(rows[0][1].startswith("Laleli · 1 roll"), rows[0][1])
        self.assertIn("20.00 of 30.00 m", rows[1][1])
        # The whole roll goes: its length, and nothing in the cut column.
        self.assertEqual(rows[2][1], "1 R-100 7 20.00 m")
        # 10 m off a 45 m roll: the roll's length, then the cut.
        self.assertEqual(rows[5][1], "1 R-200 L1 45.00 m 10.00 m")
        body = self._page(order)
        self.assertEqual(body.count('<td class="num cut"><svg'), 1)

    def test_variants_sit_under_one_parent(self):
        """K12447 once, then each variant led by its SKU — not the parent
        repeated on every line."""
        order = self._order(self.laleli, "ORD-8")
        g50 = ProductVariant.objects.create(product=self.product, variant_sku="KRP.G50")
        g93 = ProductVariant.objects.create(product=self.product, variant_sku="KRP.G93")
        self._hold(self._line(order, "20", variant=g50), "R-900", "20", "Laleli", self.laleli)
        self._hold(self._line(order, "30", variant=g93), "R-901", "30", "Laleli", self.laleli)
        self._line(order, "5", variant=g93)                     # short, same parent

        page = self._page(order)
        rows = self._rows(page)
        self.assertEqual([cls for cls, _ in rows], ["wh", "pr", "ln", "", "ln", ""])
        self.assertTrue(rows[1][1].startswith("Krep"), rows[1][1])
        self.assertTrue(rows[2][1].startswith("KRP.G50"), rows[2][1])
        self.assertIn("20.00 of 20.00 m", rows[2][1])
        self.assertTrue(rows[4][1].startswith("KRP.G93"), rows[4][1])
        self.assertIn('<span class="vsku">KRP.G50</span>', page)
        # In the house's colour, on a tint of it.
        with patch("erp.nejum_credit.brand", return_value="#944F05"):
            page = self._page(order)
        self.assertRegex(page, r"\.vsku \{[^}]*background: #F2EAE1; color: #944F05;")
        # The short list groups the same way: the parent, then its variant.
        short = self._rows(page[page.index("Not picked yet"):])
        self.assertEqual([cls for cls, _ in short], ["pr", "short"])
        self.assertIn("KRP.G93", short[1][1])

    def test_no_prices_and_no_customer_name(self):
        order = self._order(self.laleli, "ORD-2")
        self._hold(self._line(order, "20"), "R-300", "20", "Laleli", self.laleli)

        page = self._page(order)
        self.assertNotIn("Secretname", page)
        self.assertNotIn("7.77", page)
        self.assertNotIn("155.40", page)
        self.assertIn(f"Contact #{self.customer.pk}", page)
        # The QR is a link to the order, for a phone camera.
        self.assertIn('src="data:image/svg+xml', page)

    def test_lines_left_short_close_the_sheet(self):
        order = self._order(self.laleli, "ORD-3")
        self._hold(self._line(order, "50"), "R-400", "20", "Laleli", self.laleli)
        self._line(order, "5")                                   # nothing reserved

        page = self._page(order)
        short = page[page.index("Not picked yet"):]
        rows = self._rows(short)
        # Both lines are Krep, so one heading over the two.
        self.assertEqual([cls for cls, _ in rows], ["pr", "short", "short"])
        self.assertIn("30.00 m", rows[1][1])                     # 50 ordered, 20 picked
        self.assertIn("5.00 m", rows[2][1])

    def test_a_fully_picked_order_has_no_short_section(self):
        order = self._order(self.laleli, "ORD-4")
        self._hold(self._line(order, "20"), "R-500", "20", "Laleli", self.laleli)
        self.assertNotIn("Not picked yet", self._page(order))

    def test_a_split_order_prints_every_half(self):
        group = uuid.uuid4()
        laleli = self._order(self.laleli, "ORD-5", split_group=group)
        ergene = self._order(self.ergene, "ORD-6", split_group=group)
        self._hold(self._line(laleli, "20"), "R-600", "20", "Laleli", self.laleli)
        self._hold(self._line(ergene, "30"), "R-700", "30", "Ergene", self.ergene)

        page = self._page(ergene)
        self.assertIn("ORD-5 &amp; ORD-6", page)
        rows = self._rows(page)
        self.assertEqual([cls for cls, _ in rows], ["grp", "wh", "pr", "", "grp", "wh", "pr", ""])
        self.assertIn("Laleli Fabric · Order ORD-5", rows[0][1])
        self.assertIn("R-600", rows[3][1])
        self.assertIn("R-700", rows[7][1])

    def test_a_shipped_roll_prints_what_it_held(self):
        order = self._order(self.laleli, "ORD-7")
        self._hold(self._line(order, "20"), "R-800", "20", "Laleli", self.laleli)
        # Shipping takes the metres off the roll and consumes the hold.
        r = order.stock_reservations.get()
        r.stock_item.quantity_remaining = Decimal("0")
        r.stock_item.save()
        r.consumed = True
        r.save()

        rows = self._rows(self._page(order))
        self.assertEqual(rows[2][1], "1 R-800 L1 20.00 m")      # whole: no cut
