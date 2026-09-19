"""A sale takes the cost of the goods out of stock as they leave.

Run with:
    python manage.py test accounting.tests.test_cogs_posting
"""
from decimal import Decimal

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import balance_sheet, ensure_chart, reconcile
from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


class StockLeavingPostsItsCost(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.warehouse = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self.product = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="seta", sku="S1",
            quantity=Decimal("100"), cost_usd=Decimal("3.00"))
        self.roll = WarehouseProductItem.objects.create(
            product=self.product, quantity=Decimal("100"),
            quantity_remaining=Decimal("100"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4.00"))

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def _out(self, metres, **extra):
        return StockMovement.objects.create(
            product=self.product, stock_item=self.roll, movement_type="out",
            quantity=Decimal(metres), reason="Order ship Order #298", **extra)

    def test_metres_leaving_become_cost_of_goods_sold(self):
        self._out("25")
        b = self._balances()
        self.assertEqual(b["5000"], Decimal("100.00"))    # 25m x 4.00
        self.assertEqual(b["1300"], Decimal("-100.00"))
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_it_is_valued_at_what_that_roll_cost_not_the_products_price(self):
        """The roll carries 4.00 and the product's current cost is 3.00.
        Valuing old stock by today's cost revalues goods nobody re-bought."""
        self._out("10")
        self.assertEqual(self._balances()["5000"], Decimal("40.00"))

    def test_a_roll_with_no_cost_posts_nothing(self):
        self.roll.unit_cost_base = None
        self.roll.save()
        self.product.cost_usd = None
        self.product.save()
        self._out("10")
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_unshipping_puts_the_cost_back(self):
        from operating.models import Order
        self._out("25")
        order = Order.objects.create()
        StockMovement.objects.create(
            product=self.product, stock_item=self.roll, movement_type="in",
            quantity=Decimal("25"), reason="Order edit · reversed Order #298",
            order=order)
        b = self._balances()
        self.assertEqual(b["5000"], Decimal("0.00"))
        self.assertEqual(b["1300"], Decimal("0.00"))

    def test_stock_arriving_is_left_to_the_purchase_invoice(self):
        """Intake writes a purchase invoice AND a stock row. Posting the
        stock row too would count every purchase twice."""
        StockMovement.objects.create(
            product=self.product, stock_item=self.roll, movement_type="in",
            quantity=Decimal("50"), reason="Manual add")
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_a_correction_posts_nothing_yet(self):
        StockMovement.objects.create(
            product=self.product, stock_item=self.roll,
            movement_type="adjustment", quantity=Decimal("-5"),
            reason="Manual adjustment: 100m → 95m")
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_deleting_the_row_takes_the_entry_with_it(self):
        self._out("25").delete()
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_the_entry_points_back_at_the_stock_row(self):
        movement = self._out("25")
        entry = JournalEntry.objects.get()
        self.assertEqual(entry.source, movement)
        self.assertEqual(entry.book, self.book)

    def test_the_ledger_follows_the_shelves_as_goods_are_sold(self):
        """What the whole change is for: stock in the ledger moves with the
        stock on the shelves, so the two can be reconciled."""
        from accounting.services_posting import post_opening_inventory

        post_opening_inventory(self.book, date="2026-09-01")
        self.assertEqual(reconcile(self.book)["rows"][2]["difference"],
                         Decimal("0.00"))

        self.roll.quantity_remaining = Decimal("75")
        self.roll.save()
        self.product.quantity = Decimal("75")
        self.product.save()
        self._out("25")

        row = reconcile(self.book)["rows"][2]
        self.assertEqual(row["ledger"], Decimal("300.00"))       # 400 - 100
        self.assertEqual(row["subsidiary"], Decimal("300.00"))   # 75m x 4.00
        self.assertTrue(row["reconciled"])
