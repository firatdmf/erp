"""Rolls a customer picks on the storefront: in the cart, then held by the
order, in the book their warehouse belongs to.

A cart line of picked rolls is those rolls, whole; its quantity is what
they hold. Ordering it holds them at once, and each roll goes to its own
warehouse's book, so a cart off two books' shelves becomes two orders tied
by a split_group. A roll sold or cut since it was picked stops the order
and is named, rather than the customer being sold less, or something else.
See operating/storefront_stock.py and operating/web_orders.py.
"""
import json
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from authentication.client_tokens import issue
from authentication.models import CartItem, WebClient
from marketing.models import Product, ProductVariant
from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

ORDER_URL = "/operating/orders/create/"


class PickedRolls(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        settings = override_settings(CURRENT_ACCOUNT_BOOK_ID=str(self.laleli.pk))
        settings.enable()
        self.addCleanup(settings.disable)
        self.shop = Warehouse.objects.create(name="Laleli", city="Istanbul", country="TR",
                                             accounting_book=self.laleli, on_storefront=True)
        self.factory = Warehouse.objects.create(name="Ergene Fabrika", city="Tekirdağ",
                                                country="TR", accounting_book=self.ergene,
                                                on_storefront=True)

        self.cloth = Product.objects.create(title="2086", sku="2086", featured=False)
        self.white = ProductVariant.objects.create(product=self.cloth, variant_sku="2086.WHITE")
        self.rolls = {}
        for warehouse, key, meters, lot in [(self.shop, "A", "48.5", "4471"),
                                            (self.factory, "B", "52", "4471"),
                                            (self.factory, "C", "30", "4502")]:
            row, _ = WarehouseProduct.objects.get_or_create(
                warehouse=warehouse, sku="2086.WHITE",
                defaults={"name": "2086 white", "catalog_variant": self.white})
            self.rolls[key] = WarehouseProductItem.objects.create(
                product=row, barcode=f"R-{key}", quantity=Decimal(meters),
                quantity_remaining=Decimal(meters), lot_number=lot, status="in_stock")

        self.buyer = WebClient.objects.create(
            username="buyer", email="buyer@example.com", name="Buyer Ltd",
            password=make_password("pw"), is_active=True)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {issue(self.buyer)}"}

    # ── helpers ─────────────────────────────────────────────────
    def ids(self, *keys):
        return [self.rolls[k].pk for k in keys]

    def add(self, *keys, sku="2086.WHITE"):
        return self.client.post(
            reverse("authentication:add_to_cart", args=[self.buyer.pk]),
            json.dumps({"product_sku": "2086", "variant_sku": sku,
                        "stock_items": self.ids(*keys)}),
            content_type="application/json", **self.auth)

    def cart(self):
        return self.client.get(reverse("authentication:get_cart", args=[self.buyer.pk]), **self.auth).json()

    def order(self, lines):
        return self.client.post(ORDER_URL, json.dumps({
            "items": lines, "original_currency": "USD", "delivery_city": "Izmir"}),
            content_type="application/json", **self.auth)

    def picked_line(self, *keys):
        """The line the storefront's checkout sends for picked rolls."""
        return {"product_sku": "2086", "product_variant_sku": "2086.WHITE",
                "quantity": "0", "price": "4.50",
                "stock_items": [{"id": self.rolls[k].pk,
                                 "quantity": str(self.rolls[k].quantity)} for k in keys]}

    # ── the cart ────────────────────────────────────────────────
    def test_picked_rolls_go_in_the_cart_whole(self):
        response = self.add("A", "B")
        self.assertEqual(response.status_code, 201, response.content)
        line = CartItem.objects.get()
        self.assertEqual(line.quantity, Decimal("100.50"))
        self.assertEqual(line.stock_items, [{"id": self.rolls["A"].pk, "quantity": "48.50"},
                                            {"id": self.rolls["B"].pk, "quantity": "52.00"}])

    def test_more_rolls_join_the_same_line(self):
        self.add("A")
        self.add("A", "C")
        line = CartItem.objects.get()
        self.assertEqual([p["id"] for p in line.stock_items], self.ids("A", "C"))
        self.assertEqual(line.quantity, Decimal("78.50"))

    def test_a_line_of_meters_stays_apart(self):
        self.add("A")
        self.client.post(reverse("authentication:add_to_cart", args=[self.buyer.pk]),
                         json.dumps({"product_sku": "2086", "variant_sku": "2086.WHITE",
                                     "quantity": "10"}),
                         content_type="application/json", **self.auth)
        self.assertEqual(sorted((str(l.quantity), bool(l.stock_items))
                                for l in CartItem.objects.all()),
                         [("10.00", False), ("48.50", True)])

    def test_the_cart_says_where_each_roll_stands_and_whether_it_still_does(self):
        self.add("A", "B")
        roll = self.rolls["B"]
        roll.quantity_remaining = Decimal("20")
        roll.save()
        (line,) = self.cart()["cart_items"]
        self.assertEqual(
            [(r["lot"], r["city"], r["country"], r["quantity"], r["still_free"])
             for r in line["stock_items"]],
            [("4471", "Istanbul", "TR", 48.5, True), ("4471", "Tekirdağ", "TR", 52.0, False)])

    def test_a_roll_is_taken_out_and_the_last_one_takes_the_line(self):
        self.add("A", "B")
        line = CartItem.objects.get()
        url = reverse("authentication:update_cart_item", args=[self.buyer.pk, line.pk])
        self.client.put(url, json.dumps({"stock_items": self.ids("B")}),
                        content_type="application/json", **self.auth)
        line.refresh_from_db()
        self.assertEqual((line.quantity, [p["id"] for p in line.stock_items]),
                         (Decimal("52.00"), self.ids("B")))
        self.client.put(url, json.dumps({"stock_items": []}),
                        content_type="application/json", **self.auth)
        self.assertFalse(CartItem.objects.exists())

    def test_a_picked_lines_quantity_is_not_typed(self):
        self.add("A")
        line = CartItem.objects.get()
        response = self.client.put(reverse("authentication:update_cart_item", args=[self.buyer.pk, line.pk]),
                                   json.dumps({"quantity": "5"}),
                                   content_type="application/json", **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_a_roll_somebody_else_holds_cannot_be_picked(self):
        other = Order.objects.create(order_number="900")
        roll = self.rolls["B"]
        OrderStockReservation.objects.create(order=other, stock_item=roll,
                                             warehouse_product=roll.product, quantity=roll.quantity)
        response = self.add("A", "B")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["gone"], self.ids("B"))
        self.assertFalse(CartItem.objects.exists())

    def test_goods_tracked_by_variant_cannot_be_picked(self):
        duvet = Product.objects.create(title="Duvet", featured=False, unit="piece",
                                       tracking="variant")
        ProductVariant.objects.create(product=duvet, variant_sku="DUV.1")
        self.assertEqual(self.add("A", sku="DUV.1").status_code, 400)

    # ── the order ───────────────────────────────────────────────
    def test_picked_rolls_go_to_their_warehouses_book_held(self):
        response = self.order([self.picked_line("B", "C")])
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get()
        self.assertEqual(order.current_account.book, self.ergene)
        self.assertIsNone(order.split_group)
        line = order.items.get()
        self.assertEqual(line.quantity, Decimal("82"))
        self.assertEqual(
            {r.stock_item_id: r.quantity for r in OrderStockReservation.objects.filter(order=order)},
            {self.rolls["B"].pk: Decimal("52"), self.rolls["C"].pk: Decimal("30")})

    def test_a_cart_off_two_books_shelves_is_two_orders(self):
        response = self.order([self.picked_line("A", "B")])
        self.assertEqual(response.status_code, 201, response.content)
        orders = list(Order.objects.order_by("pk"))
        self.assertEqual([o.current_account.book for o in orders], [self.laleli, self.ergene])
        self.assertEqual(len({o.split_group for o in orders}), 1)
        self.assertIsNotNone(orders[0].split_group)
        self.assertEqual([o.items.get().quantity for o in orders], [Decimal("48.5"), Decimal("52")])
        self.assertEqual({o.currency.code for o in orders}, {"USD"})
        data = response.json()
        self.assertEqual(data["order_id"], orders[0].pk)
        self.assertEqual(len(data["orders"]), 2)
        self.assertIn(" & ", data["order_number"])
        self.assertEqual({o.delivery_city for o in orders}, {"Izmir"})

    def test_a_roll_gone_since_it_was_picked_stops_the_order(self):
        roll = self.rolls["B"]
        roll.quantity_remaining = Decimal("40")
        roll.save()
        response = self.order([self.picked_line("A", "B")])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["gone"], self.ids("B"))
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderStockReservation.objects.exists())

    def test_a_line_of_meters_goes_to_the_one_book_that_holds_it(self):
        only_ergene = ProductVariant.objects.create(product=self.cloth, variant_sku="2086.GOLD")
        row = WarehouseProduct.objects.create(warehouse=self.factory, name="2086 gold",
                                              sku="2086.GOLD", catalog_variant=only_ergene)
        WarehouseProductItem.objects.create(product=row, barcode="R-G", quantity=Decimal("60"),
                                            quantity_remaining=Decimal("60"), status="in_stock")
        self.order([{"product_sku": "2086", "product_variant_sku": "2086.GOLD",
                     "quantity": "12", "price": "4.50"}])
        order = Order.objects.get()
        self.assertEqual(order.current_account.book, self.ergene)
        self.assertEqual(order.items.get().quantity, Decimal("12"))
        self.assertFalse(OrderStockReservation.objects.exists())

    def test_a_line_of_meters_held_in_both_books_goes_to_the_default_one(self):
        self.order([{"product_sku": "2086", "product_variant_sku": "2086.WHITE",
                     "quantity": "12", "price": "4.50"}])
        self.assertEqual(Order.objects.get().current_account.book, self.laleli)

    # ── cutting lengths off rolls ───────────────────────────────
    def cut(self, lengths):
        return self.client.post(
            reverse("authentication:add_to_cart", args=[self.buyer.pk]),
            json.dumps({"product_sku": "2086", "variant_sku": "2086.WHITE",
                        "stock_items": [{"id": self.rolls[k].pk, "quantity": q}
                                        for k, q in lengths.items()]}),
            content_type="application/json", **self.auth)

    def test_whole_meters_are_cut_off_any_roll(self):
        self.assertEqual(self.cut({"A": "10", "B": "52"}).status_code, 201)
        line = CartItem.objects.get()
        self.assertEqual(line.stock_items, [{"id": self.rolls["A"].pk, "quantity": "10.00"},
                                            {"id": self.rolls["B"].pk, "quantity": "52.00"}])
        self.assertEqual(line.quantity, Decimal("62"))

    def test_a_whole_roll_may_measure_anything_but_a_cut_is_whole_meters(self):
        self.assertEqual(self.cut({"A": "48.5"}).status_code, 201)
        response = self.cut({"B": "12.5"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["bad"], self.ids("B"))

    def test_more_than_a_roll_holds_cannot_be_cut(self):
        response = self.cut({"C": "31"})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(CartItem.objects.exists())

    def test_cutting_a_roll_again_takes_the_new_length(self):
        self.cut({"A": "10"})
        self.cut({"A": "20", "C": "5"})
        line = CartItem.objects.get()
        self.assertEqual([(p["id"], p["quantity"]) for p in line.stock_items],
                         [(self.rolls["A"].pk, "20.00"), (self.rolls["C"].pk, "5.00")])

    def test_the_cart_changes_a_rolls_length(self):
        self.cut({"A": "10", "C": "5"})
        line = CartItem.objects.get()
        url = reverse("authentication:update_cart_item", args=[self.buyer.pk, line.pk])
        response = self.client.put(url, json.dumps({"stock_items": [
            {"id": self.rolls["A"].pk, "quantity": "15"}, {"id": self.rolls["C"].pk}]}),
            content_type="application/json", **self.auth)
        self.assertEqual(response.status_code, 200, response.content)
        line.refresh_from_db()
        self.assertEqual(line.quantity, Decimal("20"))
        bad = self.client.put(url, json.dumps({"stock_items": [
            {"id": self.rolls["A"].pk, "quantity": "15.5"}]}),
            content_type="application/json", **self.auth)
        self.assertEqual(bad.status_code, 400)

    def test_the_order_holds_the_lengths_cut(self):
        line = {"product_sku": "2086", "product_variant_sku": "2086.WHITE", "quantity": "0",
                "price": "4.50", "stock_items": [{"id": self.rolls["B"].pk, "quantity": "20"},
                                                 {"id": self.rolls["C"].pk, "quantity": "30"}]}
        self.assertEqual(self.order([line]).status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.items.get().quantity, Decimal("50"))
        self.assertEqual(
            {r.stock_item_id: r.quantity for r in OrderStockReservation.objects.filter(order=order)},
            {self.rolls["B"].pk: Decimal("20"), self.rolls["C"].pk: Decimal("30")})

    def test_a_cut_the_roll_no_longer_holds_stops_the_order(self):
        roll = self.rolls["B"]
        roll.quantity_remaining = Decimal("15")
        roll.save()
        line = {"product_sku": "2086", "product_variant_sku": "2086.WHITE", "quantity": "0",
                "price": "4.50", "stock_items": [{"id": roll.pk, "quantity": "20"}]}
        response = self.order([line])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["gone"], [roll.pk])
