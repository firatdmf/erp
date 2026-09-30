# to run this test, use the command:
# python manage.py test operating.tests.test_order_sale_on_ship

"""An order is a sale when it ships, and its history is only added to.

The sale used to post the moment an order was saved: revenue sat in 4000
for weeks before its cost reached 5000 at shipping, and the customer's
balance counted goods still on the packing floor. Now nothing reaches the
account until the goods leave.

After that, nothing written is moved. Reopening or returning the order
writes a reversal dated that day, and shipping it again a new sale, so a
month reads the same after the fact as it did at the time — the way the
stock side already cuts and restores. The one exception is a mistake
undone the same day: the sale is simply deleted.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_ledger import balance_sheet, ensure_chart
from marketing.models import Product
from operating.models import (Order, OrderItem, OrderStockReservation, Warehouse,
                              WarehouseProduct, WarehouseProductItem)
from operating.views_warehouse import apply_order_status_change


class SaleOnShipBase(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        ensure_chart()
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-501", name="Oleg", type="customer",
            default_currency=self.usd)
        self.product = Product.objects.create(title="Velvet Moss", sku="KZL000501", price=10)
        self.user = User.objects.create_user("staff_ship", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()

    def order(self, **extra):
        order = Order.objects.create(current_account=self.account, **extra)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("40.00"), price=Decimal("3.25"))
        return order

    def move(self, order, status):
        ok, code = apply_order_status_change(order, status, user=self.user)
        self.assertTrue(ok, code)
        order.refresh_from_db()

    def rows(self, kind):
        return CurrentAccountMovement.objects.filter(movement_type=kind)

    def balance(self):
        self.account.refresh_from_db()
        return self.account.cached_balance

    EARLIER = date(2026, 8, 20)

    def backdate(self):
        """As if every row so far had been written on an earlier day."""
        CurrentAccountMovement.objects.update(date=self.EARLIER)


class AnOpenOrderIsNotASale(SaleOnShipBase):

    def test_nothing_is_owed_while_it_is_being_prepared(self):
        order = self.order()
        for status in ("confirmed", "preparing", "packaging"):
            self.move(order, status)
            self.assertFalse(self.rows("order_sale").exists(), status)
        self.assertEqual(self.balance(), Decimal("0.00"))

    def test_shipping_makes_it_one_dated_the_day_it_left(self):
        order = self.order(order_date=date(2026, 9, 1))
        self.move(order, "shipped")
        [sale] = self.rows("order_sale")
        self.assertEqual(sale.amount, Decimal("130.00"))          # 40 × 3.25
        self.assertEqual(sale.date, timezone.localdate())
        self.assertEqual(self.balance(), Decimal("130.00"))

    def test_a_later_edit_keeps_the_sale_in_its_month(self):
        from accounting.services_accounts import post_order_movement
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        post_order_movement(order)
        self.assertEqual(self.rows("order_sale").get().date, self.EARLIER)


class UndoneTheSameDayLeavesNoTrace(SaleOnShipBase):
    """A click taken back the day it was made is a mistake, not history."""

    def test_reopening_deletes_the_sale(self):
        order = self.order()
        self.move(order, "shipped")
        self.move(order, "packaging")
        self.assertFalse(self.rows("order_sale").exists())
        self.assertFalse(self.rows("return_sale").exists())
        self.assertEqual(self.balance(), Decimal("0.00"))

    def test_returning_deletes_the_sale(self):
        order = self.order()
        self.move(order, "shipped")
        self.move(order, "returned")
        self.assertFalse(self.rows("order_sale").exists())
        self.assertFalse(self.rows("return_sale").exists())


class ALaterUndoIsWrittenBesideTheSale(SaleOnShipBase):
    """Shipped on an earlier day: the sale stays in its month."""

    def test_a_return_writes_the_sales_negative_today(self):
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "returned")
        sale = self.rows("order_sale").get()
        ret = self.rows("return_sale").get()
        self.assertEqual(sale.date, self.EARLIER)
        self.assertEqual(ret.date, timezone.localdate())
        self.assertEqual(ret.amount, Decimal("-130.00"))
        self.assertEqual(ret.amount_base, -sale.amount_base)
        self.assertIn("Return", ret.description)
        self.assertEqual(self.balance(), Decimal("0.00"))
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_reopening_writes_one_too(self):
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "packaging")
        self.assertEqual(self.rows("order_sale").get().date, self.EARLIER)
        self.assertIn("reopened", self.rows("return_sale").get().description)
        self.assertEqual(self.balance(), Decimal("0.00"))

    def test_shipping_again_is_a_new_sale_in_the_new_month(self):
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "returned")
        self.move(order, "shipped")
        kinds = list(CurrentAccountMovement.objects.order_by("pk")
                     .values_list("movement_type", "date"))
        today = timezone.localdate()
        self.assertEqual(kinds, [("order_sale", self.EARLIER),
                                 ("return_sale", today),
                                 ("order_sale", today)])
        self.assertEqual(self.balance(), Decimal("130.00"))

    def test_a_same_day_undo_of_the_new_sale_keeps_the_old_pair(self):
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "packaging")
        self.move(order, "shipped")
        self.move(order, "packaging")
        self.assertEqual(self.rows("order_sale").count(), 1)
        self.assertEqual(self.rows("return_sale").count(), 1)
        self.assertEqual(self.balance(), Decimal("0.00"))

    def test_it_is_returned_at_the_rate_it_was_sold_at(self):
        eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.account.default_currency = eur
        self.account.save()
        order = self.order(currency=eur)
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            self.move(order, "shipped")
        self.backdate()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            self.move(order, "returned")
        sale = self.rows("order_sale").get()
        ret = self.rows("return_sale").get()
        self.assertEqual(ret.exchange_rate, sale.exchange_rate)
        self.assertEqual(ret.amount_base + sale.amount_base, Decimal("0.00"))

    def test_cancelling_a_returned_order_keeps_its_history(self):
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "returned")
        self.move(order, "cancelled")
        self.assertEqual(self.rows("order_sale").count(), 1)
        self.assertEqual(self.rows("return_sale").count(), 1)
        self.assertEqual(self.balance(), Decimal("0.00"))

    def test_a_new_customer_takes_the_history_with_its_dates(self):
        from accounting.services_accounts import post_order_movement
        other = CurrentAccount.objects.create(
            book=self.book, code="C-502", name="Sveta", type="customer",
            default_currency=self.usd)
        order = self.order()
        self.move(order, "shipped")
        self.backdate()
        self.move(order, "returned")
        order.current_account = other
        order.save()
        post_order_movement(order)
        self.assertEqual(set(CurrentAccountMovement.objects
                             .values_list("current_account_id", flat=True)), {other.pk})
        self.assertEqual(self.rows("order_sale").get().date, self.EARLIER)
        self.assertEqual(self.balance(), Decimal("0.00"))


class GoodsComingBackReturnTheirCost(SaleOnShipBase):
    """Un-shipping restocked the metres without saying which order they
    came back from, and the ledger only reverses cost for an order's
    stock — so 5000 kept the cost of goods that were back on the shelf."""

    def test_returned_metres_go_back_into_inventory(self):
        warehouse = Warehouse.objects.create(name="Laleli Depo", accounting_book=self.book)
        wp = WarehouseProduct.objects.create(
            warehouse=warehouse, name="velvet", sku="V1",
            quantity=Decimal("100"), cost_usd=Decimal("4.00"))
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            barcode="BC-501", status="in_stock", unit_cost_base=Decimal("4.00"))
        order = self.order()
        OrderStockReservation.objects.create(
            order=order, order_item=order.items.get(), stock_item=roll,
            warehouse_product=wp, quantity=Decimal("25"))

        self.move(order, "shipped")
        rows = {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(rows["5000"], Decimal("100.00"))          # 25m × 4.00

        self.move(order, "returned")
        rows = {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(rows["5000"], Decimal("0.00"))
        self.assertEqual(rows["1300"], Decimal("0.00"))


class AnOrderOfManyRollsShipsInOneGo(SaleOnShipBase):
    """Each cut roll took about sixteen queries, most of them its cost
    going into the ledger. An order of 400 rolls (ORD-2026-000033) ran
    past the web server's timeout and could not be completed."""

    def ship_rolls(self, count):
        batch = WarehouseProduct.objects.count()
        warehouse = Warehouse.objects.create(name=f"Laleli Fabrika {batch}",
                                             accounting_book=self.book)
        wp = WarehouseProduct.objects.create(
            warehouse=warehouse, name="2003 EKRU", sku=f"2003.23-100.{batch}",
            quantity=Decimal(50 * count), cost_usd=Decimal("1.07"))
        order = self.order()
        item = order.items.get()
        for n in range(count):
            roll = WarehouseProductItem.objects.create(
                product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
                barcode=f"TLS-{batch}-{n}", status="in_stock", unit_cost_base=Decimal("1.07"))
            OrderStockReservation.objects.create(
                order=order, order_item=item, stock_item=roll,
                warehouse_product=wp, quantity=Decimal("50"))
        return order, wp

    def queries_to_ship(self, count):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        order, _wp = self.ship_rolls(count)
        with CaptureQueriesContext(connection) as ctx:
            self.move(order, "shipped")
        return len(ctx.captured_queries)

    def test_shipping_takes_as_many_queries_for_forty_rolls_as_for_four(self):
        self.queries_to_ship(4)                    # warms the lookups Django caches
        self.assertEqual(self.queries_to_ship(40), self.queries_to_ship(4))

    def test_every_roll_still_leaves_the_shelf_and_the_ledger(self):
        from accounting.models_ledger import JournalEntry
        from operating.models import StockMovement
        order, wp = self.ship_rolls(30)
        self.move(order, "shipped")

        wp.refresh_from_db()
        self.assertEqual(wp.quantity, Decimal("0"))
        self.assertEqual(set(WarehouseProductItem.objects.values_list(
            "quantity_remaining", "status")), {(Decimal("0.00"), "consumed")})
        self.assertFalse(order.stock_reservations.filter(consumed=False).exists())
        outs = StockMovement.objects.filter(movement_type="out", order=order)
        self.assertEqual(outs.count(), 30)
        # One entry per roll, as when each posted on its own.
        self.assertEqual(JournalEntry.objects.filter(
            source_type__model="stockmovement",
            source_id__in=outs.values("pk")).count(), 30)
        rows = {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(rows["5000"], Decimal("1605.00"))         # 30 × 50m × 1.07

        self.move(order, "packaging")
        wp.refresh_from_db()
        self.assertEqual(wp.quantity, Decimal("1500"))
        self.assertEqual(set(WarehouseProductItem.objects.values_list(
            "quantity_remaining", "status")), {(Decimal("50.00"), "in_stock")})
        self.assertFalse(order.stock_reservations.filter(consumed=True).exists())
        rows = {r["code"]: r["balance"]
                for r in balance_sheet(self.book)["trial_balance"]["rows"]}
        self.assertEqual(rows["5000"], Decimal("0.00"))
        self.assertEqual(rows["1300"], Decimal("0.00"))


class TheAccountPageNamesWhatIsComing(SaleOnShipBase):

    def test_open_orders_are_listed_under_the_balance(self):
        from django.urls import reverse
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        self.order()
        page = self.client.get(reverse("accounts:detail", args=[self.account.pk]))
        self.assertContains(page, "1 open order not billed yet")
        self.assertContains(page, "130.00")
