"""What the warehouse product list says about cost and about place.

Two claims the columns have to keep:

* Unit cost is the quantity-weighted average of the stock standing on the
  floor — the same figure the Total beside it is built from. It used to be
  the SKU's last-purchase price, so a row read "$5.00 x 100 m = $400" and
  nobody could tell which of the two numbers was lying.
* A combined (ortak) warehouse pools several members' shelves into one
  list, so every row has to say which shelf it came off.

Run with:
    python manage.py test operating.test_warehouse_list_columns
"""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory

from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


def _cell(html, label):
    """The text of the row cell carrying this data-label, tags stripped.

    Scoped rather than a bare assertIn: the page is full of money and of
    warehouse names, and a substring match would happily pass on somebody
    else's.
    """
    m = re.search(r'<td[^>]*data-label="%s"[^>]*>(.*?)</td>' % label,
                  html, re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else None


class UnitCostIsTheWeightedAverage(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        # cost_usd is the LAST purchase price — deliberately far from what
        # the stock on the floor actually cost, so a column reading from it
        # cannot pass by accident.
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta grey", sku="SETA-1",
            quantity=Decimal("300"), cost_usd=Decimal("9.99"),
            purchase_price=Decimal("9.99"), purchase_currency="USD")

        user = get_user_model().objects.create_user("wh", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _top(self, metres, cost, code):
        return WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal(metres),
            quantity_remaining=Decimal(metres), barcode=f"BC-{code}",
            status="in_stock",
            unit_cost_base=Decimal(cost) if cost is not None else None)

    def _list(self, **params):
        resp = self.client.get(
            reverse("operating:warehouse_detail", args=[self.wh.pk]), params)
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_it_averages_by_metre_not_by_stock_item(self):
        """A 5 m remnant must not weigh as much as a 295 m bolt."""
        self._top("295", "4.00", "a")
        self._top("5", "20.00", "b")
        # (295 x 4 + 5 x 20) / 300 = 4.2667. A plain mean of the two items
        # would report 12.00 — nearly triple.
        self.assertEqual(_cell(self._list(), "Unit cost"), "$4.27")

    def test_it_is_not_the_skus_last_purchase_price(self):
        self._top("300", "4.00", "a")
        html = self._list()
        self.assertEqual(_cell(html, "Unit cost"), "$4.00")
        self.assertNotIn("$9.99", html)

    def test_unit_cost_times_stock_comes_to_the_total_beside_it(self):
        """The whole point: one row, one arithmetic."""
        self._top("300", "4.00", "a")
        html = self._list()
        self.assertEqual(_cell(html, "Unit cost"), "$4.00")
        self.assertEqual(_cell(html, "Total"), "$1200.00")

    def test_stock_with_no_recorded_cost_shows_a_dash_not_a_guess(self):
        self._top("300", None, "a")
        self.assertEqual(_cell(self._list(), "Unit cost"), "—")

    def test_the_sign_is_the_owning_books_currency(self):
        try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺")
        self.book.base_currency = try_
        self.book.save(update_fields=["base_currency"])
        self._top("300", "4.00", "a")
        self.assertEqual(_cell(self._list(), "Unit cost"), "₺4.00")

    def test_the_grouped_view_agrees_with_the_flat_one(self):
        self._top("295", "4.00", "a")
        self._top("5", "20.00", "b")
        self.assertEqual(_cell(self._list(view="grouped"), "Unit cost"),
                         "~$4.27")


class CombinedWarehouseSaysWhichShelf(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        self.store = Warehouse.objects.create(
            name="Laleli", location="Fatih / İstanbul", accounting_book=self.book)
        self.factory = Warehouse.objects.create(
            name="Laleli Fabrika", location="Ergene / Tekirdağ",
            accounting_book=self.book)
        self.combined = Warehouse.objects.create(
            name="Ortak Perde Depo", kind="combined", accounting_book=self.book)
        self.combined.combined_sources.set([self.store, self.factory])

        user = get_user_model().objects.create_user("wh", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _stock(self, warehouse, sku, name="seta grey"):
        wp = WarehouseProduct.objects.create(
            warehouse=warehouse, name=name, sku=sku,
            quantity=Decimal("50"), cost_usd=Decimal("4.00"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=f"BC-{sku}", status="in_stock",
            unit_cost_base=Decimal("4.0000"))
        return wp

    def _list(self, warehouse, **params):
        resp = self.client.get(
            reverse("operating:warehouse_detail", args=[warehouse.pk]), params)
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def _locations(self, html):
        return [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(
                r'<td[^>]*data-label="Location"[^>]*>(.*?)</td>', html, re.S)
        ]

    def test_every_row_names_the_member_it_stands_in(self):
        self._stock(self.store, "A")
        self._stock(self.factory, "B")
        self.assertEqual(sorted(self._locations(self._list(self.combined))),
                         ["Laleli", "Laleli Fabrika"])

    def test_the_column_carries_the_members_address(self):
        self._stock(self.store, "A")
        self.assertIn('title="Fatih / İstanbul"', self._list(self.combined))

    def test_a_plain_warehouse_does_not_grow_the_column(self):
        """Every row would say the same thing — a column of one answer."""
        self._stock(self.store, "A")
        html = self._list(self.store)
        self.assertEqual(self._locations(html), [])
        # The heading, not the word: "Location" also labels the warehouse's
        # own address in the sidebar, which stays either way.
        self.assertNotIn("<th>Location</th>", html)

    def test_a_grouped_row_names_every_member_the_product_straddles(self):
        self._stock(self.store, "A")
        self._stock(self.factory, "B")
        cell = self._locations(self._list(self.combined, view="grouped"))
        self.assertEqual(len(cell), 1)          # one main product
        self.assertIn("Laleli", cell[0])
        self.assertIn("Laleli Fabrika", cell[0])

    def test_the_rows_still_span_the_table(self):
        """The extra column has to reach the full-width cells too, or the
        expanded stock items and the pager sit short of the last column."""
        wp = self._stock(self.store, "A")
        resp = self.client.get(reverse(
            "operating:warehouse_product_rolls", args=[self.combined.pk, wp.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('colspan="7"', resp.content.decode())


class TheListDoesNotJoinTheStockItems(TestCase):
    """The stock-item COUNT on each row must not be a join.

    Count("stock_items") is a reverse-relation aggregate, so Django adds a
    LEFT JOIN and groups the row by every other selected column. Those
    other columns are the correlated subqueries behind stock_value,
    stock_quantity and reserved — which then run once per JOINED STOCK
    ITEM instead of once per product. On the combined warehouse (2,011
    products over 8,343 stock items) that was 3,157 ms of server work
    against 193 ms for the same page built with a subquery.

    The counts come out identical either way, so nothing about the
    RESULT can catch a regression here — only the shape of the query
    can. Hence a test on the SQL rather than on the numbers.

    The same trap, and the same fix, is documented in warehouse_search_q.
    """

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta grey", sku="SETA-1",
            quantity=Decimal("30"))
        for n in range(3):
            WarehouseProductItem.objects.create(
                product=self.wp, quantity=Decimal("10"),
                quantity_remaining=Decimal("10"), barcode=f"BC-{n}",
                status="in_stock", unit_cost_base=Decimal("4"))

        user = get_user_model().objects.create_user("wh2", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _list_sql(self, **params):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(reverse(
                "operating:warehouse_detail", args=[self.wh.pk]), params)
            self.assertEqual(resp.status_code, 200)
        return [" ".join(q["sql"].split()).lower() for q in ctx.captured_queries]

    def _product_selects(self, sqls):
        """The queries that build the product list — the ones selecting
        warehouseproduct rows with the cost subqueries attached."""
        return [s for s in sqls
                if "from \"operating_warehouseproduct\"" in s
                and "unit_cost_base" in s]

    def test_the_outer_row_query_does_not_group_by(self):
        """Only the OUTER query matters. Each correlated subquery carries a
        GROUP BY of its own, correctly — it is the outer one, added by a
        reverse-relation Count(), that forces the subqueries to be
        re-evaluated per joined row."""
        rows = self._product_selects(self._list_sql())
        self.assertTrue(rows, "no product list query was captured")
        for sql in rows:
            outer = sql.rsplit('from "operating_warehouseproduct"', 1)[-1]
            self.assertNotIn("group by", outer)

    def test_the_row_query_does_not_join_the_stock_item_table(self):
        rows = self._product_selects(self._list_sql())
        self.assertTrue(rows, "no product list query was captured")
        for sql in rows:
            self.assertNotIn(
                'inner join "operating_warehouseproductitem"', sql)
            self.assertNotIn(
                'left outer join "operating_warehouseproductitem"', sql)

    def test_the_count_it_reports_is_still_right(self):
        html = self._list_html()
        self.assertIn("3", html)
        from operating.views_warehouse import stock_item_count_subquery
        got = (WarehouseProduct.objects.filter(pk=self.wp.pk)
               .annotate(n=stock_item_count_subquery()).first().n)
        self.assertEqual(got, 3)

    def test_a_consumed_stock_item_is_not_counted(self):
        from operating.views_warehouse import stock_item_count_subquery
        self.wp.stock_items.filter(barcode="BC-0").update(status="consumed")
        got = (WarehouseProduct.objects.filter(pk=self.wp.pk)
               .annotate(n=stock_item_count_subquery()).first().n)
        self.assertEqual(got, 2)

    def test_a_product_with_no_stock_items_counts_zero_not_null(self):
        """Coalesce, not a bare Subquery: a null would render as an empty
        cell where the old join wrote 0."""
        from operating.views_warehouse import stock_item_count_subquery
        empty = WarehouseProduct.objects.create(
            warehouse=self.wh, name="empty", sku="EMPTY-1",
            quantity=Decimal("0"))
        got = (WarehouseProduct.objects.filter(pk=empty.pk)
               .annotate(n=stock_item_count_subquery()).first().n)
        self.assertEqual(got, 0)

    def _list_html(self):
        resp = self.client.get(reverse(
            "operating:warehouse_detail", args=[self.wh.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()
