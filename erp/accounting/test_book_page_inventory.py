"""The book page counts the stock on the shelves.

Run with:
    python manage.py test accounting.test_book_page_inventory
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.services_ledger import subsidiary_equation
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class BookPageAssets(TestCase):
    """It summed cash, receivables and fixed assets only, so Ergene's page
    showed none of the $376,906.10 standing in Ergene Fabrika."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta", sku="S1",
            quantity=Decimal("0"), cost_usd=Decimal("4.00"))

        user = get_user_model().objects.create_superuser(
            "owner", "o@x.com", "pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

    def _item(self, metres, cost, product=None):
        return WarehouseProductItem.objects.create(
            product=product or self.wp, quantity=Decimal(metres),
            quantity_remaining=Decimal(metres), barcode=f"BC-{metres}-{cost}",
            status="in_stock", unit_cost_base=cost)

    def _unpriced_product(self):
        """A product with no cost either — an item alone is not enough.

        _inventory_value falls back from the item's own stamp to the
        purchase-invoice line and then to the SKU's cost, so an item is
        only genuinely unvalued when none of the three exists.
        """
        return WarehouseProduct.objects.create(
            warehouse=self.wh, name="mystery", sku="S9",
            quantity=Decimal("0"), cost_usd=None)

    def _page(self):
        resp = self.client.get(
            reverse("accounting:book_detail", args=[self.book.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.context

    def test_stock_shows_up_in_assets(self):
        self._item("100", Decimal("4.00"))
        ctx = self._page()
        self.assertEqual(ctx["eq_inventory"], Decimal("400.00"))
        self.assertEqual(ctx["eq_assets"], Decimal("400.00"))

    def test_it_values_each_item_at_what_that_item_cost(self):
        self._item("100", Decimal("4.00"))
        self._item("100", Decimal("5.00"))
        # Not 200 x the latest price.
        self.assertEqual(self._page()["eq_inventory"], Decimal("900.00"))

    def test_it_reports_the_same_inventory_as_the_balance_sheet(self):
        """Two pages, one valuation — they cannot disagree about stock."""
        self._item("100", Decimal("4.00"))
        self._item("250", Decimal("3.25"))
        self.assertEqual(self._page()["eq_inventory"],
                         subsidiary_equation(self.book)["inventory"])

    def test_an_unpriced_item_is_counted_not_valued(self):
        self._item("100", Decimal("4.00"))
        self._item("20", None, product=self._unpriced_product())
        ctx = self._page()
        self.assertEqual(ctx["eq_inventory"], Decimal("400.00"))
        self.assertEqual(ctx["eq_unvalued_items"], 1)

    def test_the_page_says_how_many_it_could_not_price(self):
        self._item("20", None, product=self._unpriced_product())
        resp = self.client.get(
            reverse("accounting:book_detail", args=[self.book.pk]))
        self.assertContains(resp, "1 unpriced")

    def test_another_books_stock_is_not_counted(self):
        other = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        wh = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=other)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="x", sku="S2", quantity=Decimal("0"),
            cost_usd=Decimal("9.00"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            barcode="BC-OTHER", status="in_stock", unit_cost_base=Decimal("9.00"))
        self.assertEqual(self._page()["eq_inventory"], Decimal("0.00"))
