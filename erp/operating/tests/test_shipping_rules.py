"""Shipping between countries: which warehouses may send to a buyer's
country, in what order the storefront offers them, the web order's check
against the delivery address, and the page where the rules are set.
See operating/shipping.py."""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from authentication.client_tokens import issue
from authentication.models import ClientAddress, WebClient
from marketing.models import Product, ProductVariant
from operating import shipping
from operating.models import (Order, ShippingRule, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

STOCK_URL = reverse("operating:storefront_stock_items")


class Rules(TestCase):
    def test_a_country_with_no_rule_takes_goods_from_anywhere(self):
        self.assertTrue(shipping.can_ship("KZ", "DE"))

    def test_a_warehouse_always_ships_inside_its_own_country(self):
        ShippingRule.objects.create(destination="TR", only_from_inside=True)
        self.assertTrue(shipping.can_ship("TR", "TR"))
        self.assertFalse(shipping.can_ship("KZ", "TR"))

    def test_named_countries_can_not_send(self):
        ShippingRule.objects.create(destination="UA", not_from=["RU"])
        self.assertFalse(shipping.can_ship("RU", "UA"))
        self.assertTrue(shipping.can_ship("TR", "UA"))

    def test_an_unknown_place_or_buyer_is_not_stopped(self):
        ShippingRule.objects.create(destination="TR", only_from_inside=True)
        self.assertTrue(shipping.can_ship("", "TR"))
        self.assertTrue(shipping.can_ship("KZ", ""))

    def test_own_country_then_ships_best_from_then_nearest(self):
        ShippingRule.objects.create(destination="RU", best_from=["KZ"])
        known = shipping.rules()
        self.assertEqual(sorted(["TR", "KZ", "RU"], key=lambda c: shipping.preference(c, "RU", known)),
                         ["RU", "KZ", "TR"])
        # Nearest: Uzbekistan is nearer Kazakhstan than Turkey; Greece nearer Turkey.
        self.assertLess(shipping.preference("KZ", "UZ"), shipping.preference("TR", "UZ"))
        self.assertLess(shipping.preference("TR", "GR"), shipping.preference("KZ", "GR"))

    def test_buyer_country_is_their_address_else_their_connection(self):
        buyer = WebClient.objects.create(username="b", email="b@example.com", name="B",
                                         password="x", is_active=True)
        self.assertEqual(shipping.buyer_country(buyer, "de"), "DE")
        self.assertEqual(shipping.buyer_country(buyer, "Germany"), "")
        ClientAddress.objects.create(client=buyer, title="Home", address="1 St", city="Almaty",
                                     country="KZ", is_default=True)
        self.assertEqual(shipping.buyer_country(buyer, "DE"), "KZ")


class StockByCountry(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.almaty = Book.objects.create(name="Almaty")
        settings = override_settings(CURRENT_ACCOUNT_BOOK_ID=str(self.laleli.pk))
        settings.enable()
        self.addCleanup(settings.disable)
        shop = Warehouse.objects.create(name="Laleli", city="Istanbul", country="TR",
                                        accounting_book=self.laleli, on_storefront=True)
        abroad = Warehouse.objects.create(name="Almaty", city="Almaty", country="KZ",
                                          accounting_book=self.almaty, on_storefront=True)
        cloth = Product.objects.create(title="2086", sku="2086", featured=False)
        variant = ProductVariant.objects.create(product=cloth, variant_sku="2086.WHITE")
        self.rolls = {}
        for warehouse, key, meters in [(shop, "TR", "40"), (abroad, "KZ", "60")]:
            row = WarehouseProduct.objects.create(warehouse=warehouse, sku="2086.WHITE",
                                                  name="2086 white", catalog_variant=variant)
            self.rolls[key] = WarehouseProductItem.objects.create(
                product=row, barcode=f"R-{key}", quantity=Decimal(meters),
                quantity_remaining=Decimal(meters), lot_number="4471", status="in_stock")
        self.buyer = WebClient.objects.create(username="buyer", email="buyer@example.com",
                                              name="Buyer", password=make_password("pw"),
                                              is_active=True)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {issue(self.buyer)}"}
        ShippingRule.objects.create(destination="TR", only_from_inside=True)

    def stock(self, to=""):
        response = self.client.get(STOCK_URL, {"sku": "2086.WHITE", "to": to}, **self.auth)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_a_buyer_in_turkey_is_offered_only_turkish_rolls(self):
        data = self.stock("TR")
        self.assertEqual(data["ship_to"], "TR")
        self.assertEqual([i["id"] for i in data["items"]], [self.rolls["TR"].pk])
        self.assertEqual([(p["location"], p["ships"]) for p in data["locations"]],
                         [("Istanbul, TR", True), ("Almaty, KZ", False)])

    def test_a_buyer_in_uzbekistan_is_offered_almaty_first(self):
        data = self.stock("UZ")
        self.assertEqual([p["location"] for p in data["locations"]], ["Almaty, KZ", "Istanbul, TR"])
        self.assertEqual(len(data["items"]), 2)

    def test_the_web_order_checks_the_delivery_country(self):
        line = {"product_sku": "2086", "product_variant_sku": "2086.WHITE", "quantity": "0",
                "price": "4.50", "stock_items": [{"id": self.rolls["KZ"].pk, "quantity": "10"}]}

        def order(country):
            return self.client.post("/operating/orders/create/", json.dumps({
                "items": [line], "original_currency": "USD", "delivery_country": country}),
                content_type="application/json", **self.auth)

        refused = order("TR")
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.json()["blocked"], [self.rolls["KZ"].pk])
        self.assertFalse(Order.objects.exists())
        self.assertEqual(order("DE").status_code, 201)


class Page(TestCase):
    URL = reverse("operating:shipping_rules")

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("boss", "b@t.com", "pw")

    def test_an_admin_sets_the_rules(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.URL).status_code, 200)
        response = self.client.post(self.URL, {
            "row": ["1", "2", "3"],
            "dest_1": "TR", "mode_1": "inside", "best_from_1": ["KZ"],
            "dest_2": "ua", "mode_2": "except", "not_from_2": ["RU", "UA", "XX"],
            "dest_3": "RU", "mode_3": "anywhere", "best_from_3": ["KZ"],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            [(r.destination, r.only_from_inside, r.not_from, r.best_from)
             for r in ShippingRule.objects.all()],
            [("RU", False, [], ["KZ"]), ("TR", True, [], []), ("UA", False, ["RU"], [])])
        page = self.client.get(self.URL)
        self.assertContains(page, 'name="not_from_3" data-field="not_from" value="RU"')
        # Rows left out are removed.
        self.client.post(self.URL, {"row": ["1"], "dest_1": "TR", "mode_1": "inside"})
        self.assertEqual(list(ShippingRule.objects.values_list("destination", flat=True)), ["TR"])

    def test_a_country_twice_or_none_is_refused(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.URL, {"row": ["1", "2"], "dest_1": "TR", "dest_2": "TR",
                                               "mode_1": "inside", "mode_2": "anywhere"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(self.URL, {"row": ["1"], "dest_1": "", "best_from_1": ["KZ"]})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ShippingRule.objects.exists())

    def test_only_an_admin_changes_them(self):
        clerk = get_user_model().objects.create_user("clerk", "c@t.com", "pw")
        self.client.force_login(clerk)
        self.assertEqual(self.client.get(self.URL).status_code, 200)
        self.client.post(self.URL, {"row": ["1"], "dest_1": "TR", "mode_1": "inside"})
        self.assertFalse(ShippingRule.objects.exists())
