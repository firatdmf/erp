"""Shipping reach: which warehouses may send to a buyer's country, in what
order the storefront offers them, the web order's check against the
delivery address, and the warehouse form that sets it.
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
from operating.models import Order, Warehouse, WarehouseProduct, WarehouseProductItem

STOCK_URL = reverse("operating:storefront_stock_items")


def warehouse(country, ships_to="everywhere", countries=(), best=()):
    return Warehouse(name=country, country=country, ships_to=ships_to,
                     ships_to_countries=list(countries), ships_best_to=list(best))


class Reach(TestCase):
    def test_a_warehouse_ships_everywhere_unless_told(self):
        self.assertTrue(shipping.can_ship(warehouse("KZ"), "DE"))

    def test_every_country_except_these(self):
        almaty = warehouse("KZ", "except", ["TR"])
        self.assertFalse(shipping.can_ship(almaty, "TR"))
        self.assertTrue(shipping.can_ship(almaty, "UA"))

    def test_only_these_countries(self):
        shop = warehouse("TR", "only", ["GR", "BG"])
        self.assertTrue(shipping.can_ship(shop, "GR"))
        self.assertFalse(shipping.can_ship(shop, "DE"))

    def test_a_warehouse_always_ships_inside_its_own_country(self):
        self.assertTrue(shipping.can_ship(warehouse("TR", "only", ["GR"]), "TR"))
        self.assertTrue(shipping.can_ship(warehouse("TR", "except", ["TR"]), "TR"))

    def test_an_unknown_buyer_is_not_stopped(self):
        self.assertTrue(shipping.can_ship(warehouse("KZ", "except", ["TR"]), ""))

    def test_own_country_then_ships_best_to_then_nearest(self):
        places = [warehouse("TR"), warehouse("KZ", best=["RU"]), warehouse("RU")]
        self.assertEqual([w.country for w in sorted(places, key=lambda w: shipping.preference(w, "RU"))],
                         ["RU", "KZ", "TR"])
        # Nearest: Uzbekistan is nearer Kazakhstan than Turkey; Greece nearer Turkey.
        self.assertLess(shipping.preference(warehouse("KZ"), "UZ"), shipping.preference(warehouse("TR"), "UZ"))
        self.assertLess(shipping.preference(warehouse("TR"), "GR"), shipping.preference(warehouse("KZ"), "GR"))

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
                                          accounting_book=self.almaty, on_storefront=True,
                                          ships_to="except", ships_to_countries=["TR"])
        cloth = Product.objects.create(title="2086", sku="2086", featured=False)
        variant = ProductVariant.objects.create(product=cloth, variant_sku="2086.WHITE")
        self.rolls = {}
        for place, key, meters in [(shop, "TR", "40"), (abroad, "KZ", "60")]:
            row = WarehouseProduct.objects.create(warehouse=place, sku="2086.WHITE",
                                                  name="2086 white", catalog_variant=variant)
            self.rolls[key] = WarehouseProductItem.objects.create(unit_cost_base=Decimal("1"),
                product=row, barcode=f"R-{key}", quantity=Decimal(meters),
                quantity_remaining=Decimal(meters), lot_number="4471", status="in_stock")
        self.buyer = WebClient.objects.create(username="buyer", email="buyer@example.com",
                                              name="Buyer", password=make_password("pw"),
                                              is_active=True)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {issue(self.buyer)}"}

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
        self.assertEqual(order("UA").status_code, 201)


class WarehouseForm(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Almaty")
        self.almaty = Warehouse.objects.create(name="Almaty", country="KZ", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser("boss", "b@t.com", "pw"))

    def post(self, **reach):
        return self.client.post(reverse("operating:warehouse_edit", args=[self.almaty.pk]), {
            "name": "Almaty", "kind": "normal", "accounting_book": str(self.book.pk),
            "country": "KZ", "on_storefront": "on", **reach})

    def test_the_form_saves_the_reach(self):
        self.assertContains(self.client.get(reverse("operating:warehouse_edit", args=[self.almaty.pk])),
                            'name="ships_to"')
        self.post(ships_to="except", ships_to_countries=["tr", "TR", "XX"], ships_best_to=["RU"])
        self.almaty.refresh_from_db()
        self.assertEqual((self.almaty.ships_to, self.almaty.ships_to_countries, self.almaty.ships_best_to),
                         ("except", ["TR"], ["RU"]))
        self.assertContains(self.client.get(reverse("operating:warehouse_edit", args=[self.almaty.pk])),
                            'name="ships_to_countries" value="TR"')

    def test_a_list_without_countries_is_every_country(self):
        self.post(ships_to="only")
        self.almaty.refresh_from_db()
        self.assertEqual((self.almaty.ships_to, self.almaty.ships_to_countries), ("everywhere", []))
        self.post(ships_to="everywhere", ships_to_countries=["TR"])
        self.almaty.refresh_from_db()
        self.assertEqual((self.almaty.ships_to, self.almaty.ships_to_countries), ("everywhere", []))
