"""Stock counts toward the book that owns the shelves it stands on.

Run with:
    python manage.py test accounting.test_inventory_attribution
"""
from decimal import Decimal

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.services_ledger import subsidiary_equation
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class InventoryAttribution(TestCase):
    """Inventory was scoped by the purchase-invoice line a roll arrived on.

    Not one roll in the company carries a purchase_invoice_item, so that
    filter matched nothing and both books reported $0.00 of inventory
    while 100,888 meters of fabric stood in Ergene Fabrika.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        self.laleli = Book.objects.create(
            name="Laleli Fabric", base_currency=self.usd)
        self.fabrika = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.ergene)

    def _roll(self, warehouse, meters, cost, status="in_stock"):
        product = WarehouseProduct.objects.create(
            warehouse=warehouse, name="seta grey", cost_usd=cost)
        roll = WarehouseProductItem.objects.create(
            product=product, quantity=meters, quantity_remaining=meters,
            status=status, unit_cost_base=cost or Decimal("1"))
        return roll

    def test_uninvoiced_stock_still_counts(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        subs = subsidiary_equation(self.ergene)
        self.assertEqual(subs["inventory"], Decimal("373.50"))

    def test_stock_belongs_to_the_warehouse_owner_only(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        self.assertEqual(subsidiary_equation(self.laleli)["inventory"],
                         Decimal("0.00"))

    def test_a_consumed_roll_is_not_an_asset(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"),
                   status="consumed")
        self.assertEqual(subsidiary_equation(self.ergene)["inventory"],
                         Decimal("0.00"))

    def test_inventory_lands_in_assets_and_the_causes_still_add_up(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        subs = subsidiary_equation(self.ergene)
        self.assertEqual(subs["assets"], Decimal("373.50"))
        # The residual is still explained exactly by its causes.
        self.assertEqual(subs["causes_total"], subs["residual"])
