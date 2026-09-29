"""The printed order is cut by where its goods are picked from: each order
under its book on the combined sheet, and its lines under the warehouse
their reserved rolls stand in. Counts, never barcodes — those are the
packing list's.

Run with:
    python manage.py test operating.tests.test_order_print_shelves
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
from marketing.models import Product
from operating.models import (Order, OrderItem, OrderStockReservation, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


class OrderPrintShelvesTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Anna")
        self.product = Product.objects.create(title="Krep", sku="KRP")
        self.user = get_user_model().objects.create_user("staff_shelves", password="pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _order(self, book, number, **kw):
        account, _ = CurrentAccount.objects.get_or_create(
            book=book, contact=self.customer,
            defaults={"code": f"C-{book.pk}", "name": "Anna", "type": "customer",
                      "default_currency": self.usd})
        return Order.objects.create(order_number=number, current_account=account,
                                    contact=self.customer, **kw)

    def _line(self, order, qty, price="2.00"):
        return OrderItem.objects.create(order=order, product=self.product,
                                        quantity=Decimal(qty), price=Decimal(price))

    def _hold(self, line, barcode, metres, warehouse, book):
        wh, _ = Warehouse.objects.get_or_create(name=warehouse, accounting_book=book)
        wp, _ = WarehouseProduct.objects.get_or_create(warehouse=wh, sku="KRP", defaults={"name": "Krep"})
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal(metres), quantity_remaining=Decimal(metres),
            barcode=barcode, status="in_stock")
        OrderStockReservation.objects.create(order=line.order, order_item=line, stock_item=roll,
                                             warehouse_product=wp, quantity=Decimal(metres))

    def _rows(self, response):
        body = response.content.decode()
        body = body[body.index("<tbody>"):body.index("</tbody>")]
        return [(cls, re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip())
                for cls, inner in re.findall(r'<tr(?: class="([^"]*)")?>(.*?)</tr>', body, re.S)]

    def _print(self, order):
        return self._rows(self.client.get(reverse("operating:order_print", args=[order.pk]),
                                          {"html": "1"}))

    def test_lines_sit_under_their_warehouse(self):
        order = self._order(self.laleli, "ORD-1")
        shop = self._line(order, "20")
        self._hold(shop, "R-1", "20", "Laleli", self.laleli)
        factory = self._line(order, "30")
        self._hold(factory, "R-2", "30", "Laleli Fabrika", self.laleli)
        loose = self._line(order, "5")                           # nothing reserved yet

        rows = self._print(order)
        self.assertEqual([cls for cls, _ in rows], ["wh", "", "wh", "", "wh", "", "grand", "sum"])
        self.assertTrue(rows[0][1].startswith("Laleli · 1 roll"), rows[0][1])
        self.assertTrue(rows[2][1].startswith("Laleli Fabrika · 1 roll"), rows[2][1])
        self.assertIn("Rolls not yet chosen", rows[4][1])
        self.assertIn("$110.00", rows[6][1])
        # Counted, never named.
        page = " ".join(text for _, text in rows)
        self.assertNotIn("R-1", page)
        self.assertNotIn("R-2", page)

    def test_a_line_across_two_warehouses_prints_under_each(self):
        order = self._order(self.laleli, "ORD-2")
        line = self._line(order, "30.3", "3.33")                # $100.899 → $100.90
        self._hold(line, "R-3", "10.1", "Laleli", self.laleli)
        self._hold(line, "R-4", "20.2", "Laleli Fabrika", self.laleli)

        lines = [text for cls, text in self._print(order) if not cls]
        self.assertEqual(len(lines), 2)
        self.assertIn("10.10 m", lines[0]); self.assertIn("$33.63", lines[0])
        self.assertIn("20.20 m", lines[1]); self.assertIn("$67.27", lines[1])   # the rest, to the cent

    def test_a_line_its_rolls_do_not_make_up_prints_whole(self):
        """Typed by hand, or picked short: no warehouse accounts for the
        rest, so the line stays one line under the warehouse holding most."""
        order = self._order(self.laleli, "ORD-3")
        line = self._line(order, "50")
        self._hold(line, "R-5", "10", "Laleli", self.laleli)
        self._hold(line, "R-6", "20", "Laleli Fabrika", self.laleli)

        rows = self._print(order)
        self.assertEqual([cls for cls, _ in rows][:2], ["wh", ""])
        self.assertTrue(rows[0][1].startswith("Laleli Fabrika · 2 rolls"), rows[0][1])
        self.assertIn("50.00 m", rows[1][1])

    def test_an_order_with_nothing_reserved_prints_no_headings(self):
        order = self._order(self.laleli, "ORD-4")
        self._line(order, "20")
        self.assertEqual([cls for cls, _ in self._print(order)], ["", "grand"])

    def test_the_combined_sheet_names_each_orders_book(self):
        a = self._order(self.laleli, "ORD-5")
        self._line(a, "10")
        b = self._order(self.ergene, "ORD-6")
        self._line(b, "10")
        rows = self._rows(self.client.get(reverse("operating:order_print_combined"),
                                          {"ids": f"{a.pk},{b.pk}", "html": "1"}))
        heads = [text for cls, text in rows if cls == "grp"]
        self.assertTrue(heads[0].startswith("Laleli Fabric · Order ORD-5"), heads[0])
        self.assertTrue(heads[1].startswith("Ergene Fabric · Order ORD-6"), heads[1])

    def test_a_split_orders_print_button_prints_both_halves(self):
        group = uuid.uuid4()
        a = self._order(self.laleli, "ORD-7", split_group=group)
        self._line(a, "10")
        b = self._order(self.ergene, "ORD-8", split_group=group)
        self._line(b, "10")
        page = self.client.get(reverse("operating:order_detail", args=[a.pk])).content.decode()
        self.assertIn(f'{reverse("operating:order_print_combined")}?ids={a.pk},{b.pk}', page)

        # Someone who may open only one half prints that half.
        self.user.member.books.remove(self.ergene)
        page = self.client.get(reverse("operating:order_detail", args=[a.pk])).content.decode()
        self.assertNotIn(reverse("operating:order_print_combined"), page)
        self.assertIn(reverse("operating:order_print", args=[a.pk]), page)

    def test_the_header_names_the_order_or_every_order(self):
        a = self._order(self.laleli, "ORD-9")
        self._line(a, "10")
        b = self._order(self.ergene, "ORD-10")
        self._line(b, "10")
        single = self.client.get(reverse("operating:order_print", args=[a.pk]), {"html": "1"})
        self.assertContains(single, '<div class="doc-type">ORD-9</div>', html=True)
        self.assertContains(single, '<span class="kind">ORDER</span>', html=True)
        self.assertNotContains(single, "kind b2b")
        combined = self.client.get(reverse("operating:order_print_combined"),
                                   {"ids": f"{a.pk},{b.pk}", "html": "1"})
        self.assertContains(combined, '<div class="doc-type">ORD-9 &amp; ORD-10</div>', html=True)
        self.assertContains(combined, '<span class="kind">ORDERS</span>', html=True)
