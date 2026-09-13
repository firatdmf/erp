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
    while 100,888 metres of fabric stood in Ergene Fabrika.
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

    def _roll(self, warehouse, metres, cost, status="in_stock"):
        product = WarehouseProduct.objects.create(
            warehouse=warehouse, name="seta grey", cost_usd=cost)
        return WarehouseProductItem.objects.create(
            product=product, quantity=metres, quantity_remaining=metres,
            status=status)

    def test_uninvoiced_stock_still_counts(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        subs = subsidiary_equation(self.ergene)
        self.assertEqual(subs["inventory"], Decimal("373.50"))
        self.assertEqual(subs["unvalued_rolls"], 0)

    def test_stock_belongs_to_the_warehouse_owner_only(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        self.assertEqual(subsidiary_equation(self.laleli)["inventory"],
                         Decimal("0.00"))

    def test_a_consumed_roll_is_not_an_asset(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"),
                   status="consumed")
        self.assertEqual(subsidiary_equation(self.ergene)["inventory"],
                         Decimal("0.00"))

    def test_a_roll_with_no_cost_basis_is_counted_not_guessed_at(self):
        self._roll(self.fabrika, Decimal("20.00"), None)
        subs = subsidiary_equation(self.ergene)
        self.assertEqual(subs["inventory"], Decimal("0.00"))
        self.assertEqual(subs["unvalued_rolls"], 1)
        self.assertEqual(subs["unvalued_metres"], Decimal("20.00"))

    def test_unvalued_rolls_are_this_book_s_not_every_book_s(self):
        """The old count was global — it could not be filtered by book."""
        other = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=self.laleli)
        self._roll(other, Decimal("55.00"), None)
        self.assertEqual(subsidiary_equation(self.ergene)["unvalued_rolls"], 0)

    def test_inventory_lands_in_assets_and_the_causes_still_add_up(self):
        self._roll(self.fabrika, Decimal("100.00"), Decimal("3.7350"))
        subs = subsidiary_equation(self.ergene)
        self.assertEqual(subs["assets"], Decimal("373.50"))
        # The residual is still explained exactly by its causes.
        self.assertEqual(subs["causes_total"], subs["residual"])
