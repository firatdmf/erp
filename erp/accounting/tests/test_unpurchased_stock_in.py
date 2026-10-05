"""An item added with no purchase behind it says why, and posts by that.

Goods bought are received on a purchase, which is what puts them in
Inventory (1300). An item typed in from the barcode lookup has no purchase:
either the warehouse's stock is being recorded for the first time, or that
was done and this item was missed. Before the form asked, it posted nothing
and stamped no cost — the shelves gained the item and the ledger did not.

Run with:
    python manage.py test accounting.tests.test_unpurchased_stock_in
"""
from decimal import Decimal

from django.urls import reverse

from accounting.services_ledger import balance_sheet, reconcile
from accounting.tests import test_received_purchase_edit as base
from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


class UnpurchasedStockInTest(base.TestCase):
    """The purchase: 30 m (KRV-A) and 20 m (KRV-B) of K24644.G07 at 3.50."""
    setUp = base.ReceivedPurchaseEditTest.setUp

    def _add(self, **fields):
        data = {"commit": "true", "sku": "K24644.G07", "name": "G07",
                "quantity": "10", "barcode": "S27815"}
        data.update(fields)
        return self.client.post(
            reverse("operating:warehouse_roll_scan", args=[self.wh.pk]), data)

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def _assert_shelves_match_the_ledger(self):
        self.assertTrue(balance_sheet(self.book)["balanced"])
        inventory = reconcile(self.book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])

    def test_a_found_item_comes_back_off_shrinkage_at_the_products_cost(self):
        r = self._add(reason="found")
        self.assertTrue(r.json()["success"], r.json())

        roll = WarehouseProductItem.objects.get(barcode="S27815")
        self.assertEqual(roll.product.sku, "K24644.G07")
        self.assertEqual((roll.quantity, roll.quantity_remaining, roll.unit_cost_base),
                         (Decimal("10.00"), Decimal("10.00"), Decimal("3.5000")))
        self.assertEqual(roll.product.quantity, Decimal("60.00"))
        mv = StockMovement.objects.get(stock_item=roll)
        self.assertEqual((mv.movement_type, mv.purpose, mv.reason), ("in", "found", "Found item"))

        b = self._balances()
        self.assertEqual(b["1300"], Decimal("210.00"))        # 175 + 10 m x 3.50
        self.assertEqual(abs(b["5120"]), Decimal("35.00"))
        self.assertNotIn("3100", {c for c, v in b.items() if v})
        self._assert_shelves_match_the_ledger()

    def test_opening_stock_goes_against_opening_balance_equity(self):
        r = self._add(reason="opening", sku="NEW.SKU", name="New", barcode="OPEN-1",
                      purchase_price="2", purchase_currency="USD")
        self.assertTrue(r.json()["success"], r.json())

        roll = WarehouseProductItem.objects.get(barcode="OPEN-1")
        self.assertEqual(roll.unit_cost_base, Decimal("2.0000"))
        self.assertEqual(StockMovement.objects.get(stock_item=roll).purpose, "opening")
        b = self._balances()
        self.assertEqual(b["1300"], Decimal("195.00"))        # 175 + 10 x 2.00
        self.assertEqual(abs(b["3100"]), Decimal("20.00"))
        self.assertFalse(b.get("5120"))
        self._assert_shelves_match_the_ledger()

    def test_a_new_sku_always_gets_its_catalogue_product(self):
        """There is no leaving it out: the form's old tick box is gone, and a
        post that still sends it unticked is synced all the same."""
        r = self._add(reason="opening", sku="NEW.SKU", name="New", barcode="OPEN-1",
                      purchase_price="2", purchase_currency="USD", catalog_sync="0")
        self.assertTrue(r.json()["success"], r.json())
        product = WarehouseProductItem.objects.get(barcode="OPEN-1").product
        self.assertIsNotNone(product.catalog_variant_id)
        self.assertEqual(product.catalog_variant.variant_sku, "NEW.SKU")

    def test_an_existing_product_keeps_the_variant_it_has(self):
        before = WarehouseProduct.objects.get(warehouse=self.wh, sku="K24644.G07").catalog_variant_id
        r = self._add(reason="found", catalog_base_name="Something else",
                      catalog_attribute="color", catalog_value="RED")
        self.assertTrue(r.json()["success"], r.json())
        self.assertIsNone(r.json()["catalog"])
        self.assertEqual(
            WarehouseProduct.objects.get(warehouse=self.wh, sku="K24644.G07").catalog_variant_id, before)

    def test_no_reason_is_refused_and_nothing_is_written(self):
        r = self._add()
        self.assertEqual(r.status_code, 400)
        self.assertFalse(WarehouseProductItem.objects.filter(barcode="S27815").exists())
        self.assertEqual(self._balances()["1300"], Decimal("175.00"))

    def test_an_item_with_no_cost_is_added_and_posts_nothing(self):
        r = self._add(reason="opening", sku="NEW.SKU", name="New", barcode="OPEN-1")
        self.assertTrue(r.json()["success"], r.json())
        roll = WarehouseProductItem.objects.get(barcode="OPEN-1")
        self.assertIsNone(roll.unit_cost_base)
        self.assertEqual(self._balances()["1300"], Decimal("175.00"))

    def test_a_barcode_held_in_another_warehouse_is_refused(self):
        other = Warehouse.objects.create(name="Shop", accounting_book=self.book)
        wp = WarehouseProduct.objects.create(warehouse=other, name="X", sku="X")
        WarehouseProductItem.objects.create(product=wp, quantity=5, quantity_remaining=5,
                                            barcode="S27815")
        r = self._add(reason="found")
        self.assertFalse(r.json()["success"])
        self.assertIn("Shop", r.json()["error"])
        self.assertEqual(WarehouseProductItem.objects.filter(barcode="S27815").count(), 1)

    def test_the_second_quality_flag_is_saved(self):
        self.assertTrue(self._add(reason="found", is_second="1").json()["success"])
        self.assertTrue(WarehouseProductItem.objects.get(barcode="S27815").is_second)

    def test_the_form_finds_the_product_and_what_it_costs(self):
        r = self.client.get(
            reverse("operating:warehouse_product_search", args=[self.wh.pk]), {"q": "k24644"})
        rows = r.json()["results"]
        self.assertEqual([(x["sku"], x["quantity"], x["cost"], x["in_warehouse"]) for x in rows],
                         [("K24644.G07", 50.0, 3.5, True)])

    def test_a_sku_held_only_in_another_warehouse_is_offered_and_linked(self):
        """The same cloth kept in the book's other warehouse: the form lists
        it, and saving opens its row here on the same catalogue variant, at
        what it costs there."""
        shop = Warehouse.objects.create(name="Shop", accounting_book=self.book)
        rows = self.client.get(
            reverse("operating:warehouse_product_search", args=[shop.pk]),
            {"q": "k24644"}).json()["results"]
        self.assertEqual([(x["sku"], x["in_warehouse"], x["cost"]) for x in rows],
                         [("K24644.G07", False, 3.5)])

        r = self.client.post(
            reverse("operating:warehouse_roll_scan", args=[shop.pk]),
            {"commit": "true", "reason": "found", "sku": "K24644.G07", "name": "ignored",
             "quantity": "10", "barcode": "S27815"})
        self.assertTrue(r.json()["success"], r.json())
        roll = WarehouseProductItem.objects.get(barcode="S27815")
        first = WarehouseProduct.objects.get(warehouse=self.wh, sku="K24644.G07")
        self.assertEqual(roll.product.warehouse, shop)
        self.assertEqual(roll.product.catalog_variant_id, first.catalog_variant_id)
        self.assertEqual(roll.unit_cost_base, Decimal("3.5000"))
        self.assertEqual(self._balances()["1300"], Decimal("210.00"))
        self._assert_shelves_match_the_ledger()

    def test_the_warehouse_page_asks_which_of_the_two_it_is(self):
        page = self.client.get(reverse("operating:warehouse_detail", args=[self.wh.pk]))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn("blAddItem(\\'opening\\')", html)
        self.assertIn("blAddItem(\\'found\\')", html)
        self.assertEqual(html.count('type="radio" name="rsReason"'), 2)
