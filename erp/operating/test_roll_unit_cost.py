"""A stock item remembers what it cost, so the ledger can spend that figure.

Run with:
    python manage.py test operating.test_roll_unit_cost
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.services_ledger import subsidiary_equation

from .models import Warehouse, WarehouseProduct, WarehouseProductItem
from .views_warehouse import _add_stock_to_variant


class StampedAtIntake(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self._next = 0

    def _mint(self):
        self._next += 1
        return f"BC-{self._next:04d}"

    def _product(self, cost):
        return WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta grey", sku="SETA-1",
            quantity=Decimal("0"), cost_usd=cost)

    def _receive(self, wp, metres, unit_cost=None):
        _, ids = _add_stock_to_variant(
            wp, [{"qty": str(metres)}], self._mint, None, unit_cost=unit_cost)
        return WarehouseProductItem.objects.get(pk=ids[0])

    def test_a_received_stock_item_carries_the_batch_price(self):
        roll = self._receive(self._product(Decimal("4.00")), 100)
        self.assertEqual(roll.unit_cost_base, Decimal("4.0000"))

    def test_a_caller_can_override_the_price(self):
        roll = self._receive(self._product(Decimal("4.00")), 100,
                             unit_cost=Decimal("3.5000"))
        self.assertEqual(roll.unit_cost_base, Decimal("3.5000"))

    def test_a_later_batch_does_not_reprice_the_earlier_stock_item(self):
        """The bug this field exists to prevent. cost_usd is a
        last-purchase price, so without the stamp the first 100m would be
        silently revalued from $4.00 to $5.00 by the second delivery."""
        wp = self._product(Decimal("4.00"))
        first = self._receive(wp, 100)

        # A second delivery arrives dearer; intake rewrites the SKU cost.
        wp.cost_usd = Decimal("5.00")
        wp.save(update_fields=["cost_usd"])
        second = self._receive(wp, 100)

        first.refresh_from_db()
        self.assertEqual(first.unit_cost_base, Decimal("4.0000"))
        self.assertEqual(second.unit_cost_base, Decimal("5.0000"))

    def test_the_balance_sheet_values_each_stock_item_at_its_own_cost(self):
        wp = self._product(Decimal("4.00"))
        self._receive(wp, 100)
        wp.cost_usd = Decimal("5.00")
        wp.save(update_fields=["cost_usd"])
        self._receive(wp, 100)

        # 100 x 4.00 + 100 x 5.00. Valuing both at the latest price would
        # report 1000.00 and invent 100.00 that nobody paid.
        self.assertEqual(subsidiary_equation(self.book)["inventory"],
                         Decimal("900.00"))

    def test_a_stock_item_with_no_price_anywhere_is_counted_not_guessed_at(self):
        self._receive(self._product(None), 20)
        subs = subsidiary_equation(self.book)
        self.assertEqual(subs["inventory"], Decimal("0.00"))
        self.assertEqual(subs["unvalued_rolls"], 1)


class BackfillFromSkuCost(TestCase):
    """Migration 0079, exercised on real rows the way 0077's backfill is."""

    @staticmethod
    def _backfill():
        """Call migration 0079's backfill against the live app registry.

        0079 predates the WarehouseProductRoll -> WarehouseProductItem
        rename and asks for the model by its historical name, which is
        correct: a migration must see the state as it stood when it ran.
        The live registry only knows the new name, so the shim answers to
        the old one. Everything else is the real registry, so the query
        this exercises is the one that runs against production.
        """
        from importlib import import_module

        from django.apps import apps as registry

        class _AsItWasThen:
            @staticmethod
            def get_model(app_label, model_name):
                if model_name == "WarehouseProductRoll":
                    model_name = "WarehouseProductItem"
                return registry.get_model(app_label, model_name)

        module = import_module(
            "operating.migrations.0079_backfill_roll_unit_cost_base")
        module.stamp_cost(_AsItWasThen, None)

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=book)

    def _top(self, cost, sku):
        wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta", sku=sku, quantity=Decimal("0"),
            cost_usd=cost)
        return WarehouseProductItem.objects.create(
            product=wp, meters=Decimal("50"), meters_remaining=Decimal("50"),
            barcode=f"BC-{sku}", status="in_stock")

    def test_it_stamps_the_skus_cost(self):
        roll = self._top(Decimal("4.40"), "A")
        WarehouseProductItem.objects.update(unit_cost_base=None)
        self._backfill()
        roll.refresh_from_db()
        self.assertEqual(roll.unit_cost_base, Decimal("4.4000"))

    def test_it_leaves_an_unpriced_sku_null_rather_than_zero(self):
        roll = self._top(None, "B")
        self._backfill()
        roll.refresh_from_db()
        self.assertIsNone(roll.unit_cost_base)

    def test_it_does_not_overwrite_a_stock_item_already_stamped(self):
        """Re-running must not pull a stock item back to the current SKU price."""
        roll = self._top(Decimal("5.00"), "C")
        WarehouseProductItem.objects.filter(pk=roll.pk).update(
            unit_cost_base=Decimal("4.0000"))
        self._backfill()
        roll.refresh_from_db()
        self.assertEqual(roll.unit_cost_base, Decimal("4.0000"))

    def test_it_is_one_query_not_one_per_stock_item(self):
        for i in range(8):
            self._top(Decimal("4.40"), f"D{i}")
        WarehouseProductItem.objects.update(unit_cost_base=None)
        with self.assertNumQueries(1):
            self._backfill()


class ShownOnThePage(TestCase):
    """The figure is no use to anyone if only the ledger can read it."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta grey", sku="SETA-1",
            quantity=Decimal("0"), cost_usd=Decimal("4.40"))

        user = get_user_model().objects.create_user("wh", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _top(self, cost):
        return WarehouseProductItem.objects.create(
            product=self.wp, meters=Decimal("19.50"),
            meters_remaining=Decimal("19.50"), barcode="BC-1",
            status="in_stock", unit_cost_base=cost)

    def _page(self):
        resp = self.client.get(reverse(
            "operating:warehouse_product_detail",
            args=[self.wh.pk, self.wp.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_the_product_page_shows_what_the_stock_item_cost(self):
        self._top(Decimal("4.4000"))
        # Scoped to the cost cell: the page carries other money too, and a
        # bare "$4.40" would pass on somebody else's figure.
        self.assertIn('class="roll-cost">$4.40', self._page())

    def test_it_shows_the_metres_still_on_the_stock_item_at_that_cost(self):
        self._top(Decimal("4.4000"))
        # 19.50 m x 4.40
        self.assertIn("$85.80", self._page())

    def test_the_sign_is_the_owning_books_currency_not_a_hardcoded_dollar(self):
        try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺")
        self.book.base_currency = try_
        self.book.save(update_fields=["base_currency"])
        self._top(Decimal("4.4000"))
        html = self._page()
        self.assertIn('class="roll-cost">₺4.40', html)
        self.assertNotIn('class="roll-cost">$4.40', html)

    def test_a_book_with_no_base_currency_prints_the_bare_amount(self):
        """Better a number with no sign than one wearing the wrong one."""
        self.book.base_currency = None
        self.book.save(update_fields=["base_currency"])
        self._top(Decimal("4.4000"))
        html = self._page()
        self.assertIn('class="roll-cost">4.40', html)
        self.assertNotIn('class="roll-cost">$4.40', html)

    def test_an_unpriced_stock_item_shows_a_dash_not_a_zero(self):
        self._top(None)
        html = self._page()
        self.assertNotIn('class="roll-cost">', html)
        self.assertIn("No cost recorded for this roll.", html)


class PricingCardIsWeighted(TestCase):
    """The Pricing card sums the stock_items, rather than pricing them all at the
    latest one. Two stock items bought at different prices are the whole test:
    quantity x cost_usd cannot tell them apart and the sum can."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta grey", sku="SETA-1",
            quantity=Decimal("200"), cost_usd=Decimal("5.00"))

        user = get_user_model().objects.create_user("wh2", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _top(self, metres, cost, barcode):
        return WarehouseProductItem.objects.create(
            product=self.wp, meters=metres, meters_remaining=metres,
            barcode=barcode, status="in_stock", unit_cost_base=cost)

    def _page(self):
        resp = self.client.get(reverse(
            "operating:warehouse_product_detail", args=[self.wh.pk, self.wp.pk]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_total_value_sums_what_each_stock_item_cost(self):
        self._top(Decimal("100"), Decimal("4.0000"), "BC-A")
        self._top(Decimal("100"), Decimal("5.0000"), "BC-B")
        # 100x4 + 100x5 = 900. quantity x cost_usd would say 200x5 = 1,000.
        html = self._page()
        self.assertIn('class="stock-value">$900.00', html)
        self.assertNotIn("1,000.00", html)

    def test_unit_cost_is_the_metre_weighted_average(self):
        self._top(Decimal("100"), Decimal("4.0000"), "BC-A")
        self._top(Decimal("300"), Decimal("5.0000"), "BC-B")
        # (100x4 + 300x5) / 400 = 4.75, not the plain mean of 4.50.
        html = self._page()
        self.assertIn('class="avg-cost">$4.7500', html)

    def test_an_unpriced_stock_item_is_left_out_of_the_average(self):
        """In the denominator it would report stock cheaper than anything
        actually on the floor."""
        self._top(Decimal("100"), Decimal("4.0000"), "BC-A")
        self._top(Decimal("100"), None, "BC-B")
        html = self._page()
        self.assertIn('class="avg-cost">$4.0000', html)
        self.assertIn('class="stock-value">$400.00', html)

    def test_no_priced_stock_at_all_shows_a_dash(self):
        self._top(Decimal("100"), None, "BC-A")
        html = self._page()
        self.assertNotIn('class="avg-cost"', html)
        self.assertNotIn('class="stock-value"', html)

    def test_it_agrees_with_the_balance_sheet(self):
        self._top(Decimal("100"), Decimal("4.0000"), "BC-A")
        self._top(Decimal("100"), Decimal("5.0000"), "BC-B")
        self.assertEqual(subsidiary_equation(self.book)["inventory"],
                         Decimal("900.00"))
        self.assertIn('class="stock-value">$900.00', self._page())


class DerivedNotStored(TestCase):
    """with_stock_costs / total_value_usd read the stock items every time.

    More than ten code paths move metres — several by an incremental
    delta rather than a recompute — so a stored average would fall out of
    step with the shelf at the first one anybody forgot.
    """

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="seta", sku="SETA-1",
            quantity=Decimal("400"), cost_usd=Decimal("5.00"))

    def _top(self, metres, cost, barcode):
        return WarehouseProductItem.objects.create(
            product=self.wp, meters=metres, meters_remaining=metres,
            barcode=barcode, status="in_stock", unit_cost_base=cost)

    def _annotated(self):
        return WarehouseProduct.with_stock_costs(
            WarehouseProduct.objects.filter(pk=self.wp.pk)).first()

    def test_the_average_is_weighted_by_metres(self):
        self._top(Decimal("100"), Decimal("4.0000"), "A")
        self._top(Decimal("300"), Decimal("5.0000"), "B")
        # (100x4 + 300x5) / 400 = 4.75; the plain mean would say 4.50.
        self.assertEqual(round(self._annotated().avg_cost, 4),
                         Decimal("4.7500"))

    def test_it_follows_metres_leaving_without_anything_recomputing(self):
        a = self._top(Decimal("100"), Decimal("4.0000"), "A")
        self._top(Decimal("300"), Decimal("5.0000"), "B")
        # Cut the cheap stock item down the way a stock-out would, touching
        # nothing else — no save on the product, no recompute anywhere.
        WarehouseProductItem.objects.filter(pk=a.pk).update(
            meters_remaining=Decimal("0"), status="consumed")
        self.assertEqual(round(self._annotated().avg_cost, 4),
                         Decimal("5.0000"))
        self.assertEqual(round(self._annotated().stock_value, 2),
                         Decimal("1500.00"))

    def test_a_consumed_stock_item_is_not_worth_anything(self):
        self._top(Decimal("100"), Decimal("4.0000"), "A")
        WarehouseProductItem.objects.update(status="consumed")
        self.assertIsNone(self._annotated().avg_cost)

    def test_the_warehouse_total_sums_the_stock(self):
        self._top(Decimal("100"), Decimal("4.0000"), "A")
        self._top(Decimal("100"), Decimal("5.0000"), "B")
        # quantity(400) x cost_usd(5.00) would have said 2,000.00.
        self.assertEqual(self.wh.total_value_usd(), Decimal("900.0000"))

    def test_the_warehouse_total_leaves_out_what_it_cannot_price(self):
        self._top(Decimal("100"), Decimal("4.0000"), "A")
        self._top(Decimal("100"), None, "B")
        self.assertEqual(self.wh.total_value_usd(), Decimal("400.0000"))

    def test_the_warehouse_total_matches_the_balance_sheet(self):
        self._top(Decimal("100"), Decimal("4.0000"), "A")
        self._top(Decimal("100"), Decimal("5.0000"), "B")
        self.assertEqual(
            self.wh.total_value_usd().quantize(Decimal("0.01")),
            subsidiary_equation(self.book)["inventory"])
