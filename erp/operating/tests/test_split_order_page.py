"""An order split across books is one order on screen.

Two orders in the books — one per book, each billing its own account — and
one order on the page: named by both numbers, listing every half's lines and
totals. Whoever may open one half sees the whole order, so a sales rep who
holds only Laleli can follow the Ergene half of her customer's order — its
lines, prices and total — without ever reaching the Ergene account.

Run with:
    python manage.py test operating.tests.test_split_order_page
"""
import re
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem


class SplitOrderPage(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        customer = Contact.objects.create(name="Anna Lugansk")
        group = uuid.uuid4()
        self.laleli_half = self._half(self.laleli, "ORD-2026-000023", customer, group, usd,
                                      "Krep", Decimal("2.50"))
        self.ergene_half = self._half(self.ergene, "ORD-2026-000024", customer, group, usd,
                                      "Tul Ergene", Decimal("7.25"))

        self.user = User.objects.create_user("ruzana", password="pw")
        self.user.member.books.add(self.laleli)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.user.member.permissions.add(Permission.objects.get_or_create(name="sales_rep")[0])
        self.client.force_login(self.user)

    def _half(self, book, number, customer, group, currency, title, price):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{book.pk}", name=f"Anna ({book.name})", type="customer",
            contact=customer, default_currency=currency)
        order = Order.objects.create(order_number=number, current_account=account,
                                     contact=customer, currency=currency, split_group=group)
        product = Product.objects.create(title=title, sku=title[:6])
        OrderItem.objects.create(order=order, quantity=Decimal("10"), price=price, product=product,
                                 product_variant=product.variants.create(variant_sku=title[:6]))
        return order

    def _page(self, order):
        return self.client.get(reverse("operating:order_detail", kwargs={"pk": order.pk}))

    def test_the_page_is_named_by_both_halves(self):
        resp = self._page(self.laleli_half)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ORD-2026-000023 &amp; ORD-2026-000024")

    def test_the_rep_sees_the_other_book_s_lines_prices_and_total(self):
        resp = self._page(self.laleli_half)
        self.assertContains(resp, "Tul Ergene")
        self.assertContains(resp, "$7.25")
        self.assertContains(resp, "$72.50")          # the Ergene half's total
        self.assertContains(resp, "$97.50")          # 25.00 + 72.50

    def test_every_half_s_lines_are_in_one_table_with_one_set_of_totals(self):
        html = self._page(self.laleli_half).content.decode()
        pane = html[html.index('data-item-pane="current"'):html.index('/data-item-pane="current"')]
        self.assertEqual(pane.count("<table"), 1)
        table = pane[pane.index("<table"):pane.index("</table>")]
        self.assertIn("Krep", table)
        self.assertIn("Tul Ergene", table)
        # A row over each book's lines says whose they are.
        self.assertEqual(table.count('class="od-grp"'), 2)
        self.assertLess(table.index("Laleli Fabric"), table.index("Krep"))
        self.assertLess(table.index("Ergene Fabric"), table.index("Tul Ergene"))
        # Each book's lines are added up under them; the foot has the one total.
        self.assertEqual(table.count('class="od-sub"'), 2)
        self.assertRegex(table, r"(?s)Krep.*?<b data-order-subtotal>\$25\.00</b>.*Tul Ergene.*?<b>\$72\.50</b>")
        # Its layout is fixed: every row keeps to the header's seven columns.
        for row in re.findall(r"(?s)<tr[ >].*?</tr>", table):
            cells = re.findall(r"<t[dh][ >]", row)
            self.assertEqual(len(cells), 7, row[:120])
            self.assertNotIn("colspan", row)
        self.assertEqual(pane.count("Grand total"), 1)
        self.assertEqual(pane.count("Subtotal"), 2)
        self.assertRegex(pane, r"Grand total</span>\s*<span data-combined-total>\$97\.50</span>")

    def test_scanned_rolls_cost_and_profit_count_every_half(self):
        from marketing.models import Product
        from operating.models import OrderStockReservation, Warehouse, WarehouseProduct, WarehouseProductItem
        ProductVariant.objects.filter(product__title="Krep").update(variant_cost=Decimal("1.00"))
        ProductVariant.objects.filter(product__title="Tul Ergene").update(variant_cost=Decimal("3.00"))
        for half, meters in ((self.laleli_half, "10"), (self.ergene_half, "4.5")):
            wh = Warehouse.objects.create(name=f"WH {half.pk}", accounting_book=half.current_account.book)
            wp = WarehouseProduct.objects.create(warehouse=wh, name="roll", sku=f"R{half.pk}")
            roll = WarehouseProductItem.objects.create(
                product=wp, barcode=f"B{half.pk}", quantity=Decimal("50"))
            OrderStockReservation.objects.create(
                order=half, stock_item=roll, warehouse_product=wp,
                order_item=half.items.get(), quantity=Decimal(meters))
        # Someone who may open both books and may see what an order made.
        self.user.member.books.add(self.ergene)
        self.user.member.permissions.clear()
        self.user.member.permissions.add(Permission.objects.get_or_create(name="view_profit")[0])
        resp = self._page(self.laleli_half)
        self.assertContains(resp, "2 rolls · 14.50 m")
        # A roll, once its line is opened, says which warehouse it stands in.
        from django.template.loader import render_to_string
        roll = self.laleli_half.stock_reservations.get()
        pill = lambda: render_to_string("operating/partials/od_top_row.html", {"r": roll})
        self.assertIn(f'<i class="fa fa-warehouse"></i> WH {self.laleli_half.pk}</span>', pill())
        # "Cut" is for a roll that was really cut: shipped, for less than it held.
        self.assertNotIn("cut", pill())            # 10 m held for the order, nothing cut yet
        roll.consumed = True
        roll.stock_item.quantity_remaining = Decimal("40")
        self.assertIn("cut 10 m out of 50 m", pill())
        roll.stock_item.quantity_remaining = Decimal("0")
        roll.quantity = Decimal("50")
        self.assertNotIn("cut", pill())            # the whole roll went
        self.assertRegex(resp.content.decode(), r"data-order-cost[^>]*>\$40\.00<")    # 10 + 30
        self.assertRegex(resp.content.decode(), r"data-order-profit[^>]*>\$57\.50<")  # 97.50 - 40

    def test_the_other_book_s_cost_stays_with_those_who_may_open_it(self):
        from marketing.models import Product
        ProductVariant.objects.filter(product__title="Krep").update(variant_cost=Decimal("1.00"))
        ProductVariant.objects.filter(product__title="Tul Ergene").update(variant_cost=Decimal("3.00"))
        self.user.member.permissions.clear()  # Laleli only, but shown profit
        self.user.member.permissions.add(Permission.objects.get_or_create(name="view_profit")[0])
        resp = self._page(self.laleli_half)
        self.assertRegex(resp.content.decode(), r"data-order-cost[^>]*>\$10\.00<")

    def test_an_admin_sees_every_line_s_cost_and_the_whole_order_s(self):
        from marketing.models import Product
        ProductVariant.objects.filter(product__title="Krep").update(variant_cost=Decimal("1.00"))
        ProductVariant.objects.filter(product__title="Tul Ergene").update(variant_cost=Decimal("3.00"))
        self.user.member.permissions.clear()
        self.user.is_superuser = True  # Laleli is still her only book
        self.user.save()
        html = self._page(self.laleli_half).content.decode()
        other = html[html.index(f'id="od-half-{self.ergene_half.pk}"'):]
        other = other[:other.index("</tbody>")]
        self.assertIn("$3.00", other)
        self.assertRegex(html, r"data-order-cost[^>]*>\$40\.00<")

    def test_the_other_book_s_line_costs_are_an_admin_s_only(self):
        from marketing.models import Product
        ProductVariant.objects.filter(product__title="Tul Ergene").update(variant_cost=Decimal("3.00"))
        self.user.member.books.add(self.ergene)
        self.user.member.permissions.clear()
        self.user.member.permissions.add(Permission.objects.get_or_create(name="view_profit")[0])
        html = self._page(self.laleli_half).content.decode()
        other = html[html.index(f'id="od-half-{self.ergene_half.pk}"'):]
        self.assertNotIn("$3.00", other[:other.index("</tbody>")])

    def test_but_not_the_other_book_s_account(self):
        resp = self._page(self.laleli_half)
        self.assertNotContains(resp, "Anna (Ergene Fabric)")
        self.assertNotContains(resp, "Open this half")

    def test_opening_the_other_half_leads_to_the_one_she_may_open(self):
        resp = self._page(self.ergene_half)
        self.assertRedirects(resp, reverse("operating:order_detail",
                                           kwargs={"pk": self.laleli_half.pk}))

    def test_an_unsplit_order_of_another_book_stays_hidden(self):
        account = CurrentAccount.objects.create(
            book=self.ergene, code="C-X", name="Someone", type="customer",
            default_currency=CurrencyCategory.objects.get(code="USD"))
        other = Order.objects.create(order_number="ORD-2026-000099", current_account=account)
        self.assertEqual(self._page(other).status_code, 404)

    def test_someone_holding_both_books_can_open_either_half(self):
        self.user.member.books.add(self.ergene)
        resp = self._page(self.laleli_half)
        self.assertContains(resp, "Open this half")
        self.assertEqual(self._page(self.ergene_half).status_code, 200)

    def test_the_order_list_tags_the_split(self):
        resp = self.client.get(reverse("operating:order_list_scoped", kwargs={"book_id": self.laleli.pk}))
        self.assertContains(resp, "Split with")
        self.assertContains(resp, "Ergene Fabric")

    def test_the_order_list_shows_the_whole_order_s_total(self):
        resp = self.client.get(reverse("operating:order_list_scoped", kwargs={"book_id": self.laleli.pk}))
        html = resp.content.decode()
        self.assertRegex(html, r'(?s)class="num ord-total">\s*\$97\.50\s*<span[^>]*>This book: \$25\.00</span>')

    def test_the_rep_prints_the_whole_order(self):
        resp = self.client.get(reverse("operating:order_print", kwargs={"pk": self.laleli_half.pk}) + "?html=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Krep")
        self.assertContains(resp, "Tul Ergene")
        self.assertContains(resp, "$97.50")
        self.assertNotContains(resp, "Anna (Ergene Fabric)")
