"""The stock a signed-in business customer may pick from on the storefront.

Cloth is offered roll by roll, each with its length, its lot and where it
stands; ready-made goods, whose barcode names the variant, as a quantity
per place. Only free stock, only for a signed-in customer, and nothing the
customer has no business reading: cost, barcodes, books, street address.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.client_tokens import issue
from authentication.models import WebClient
from marketing.models import Product, ProductVariant
from operating.models import (Order, OrderStockReservation, Warehouse,
                              WarehouseProduct, WarehouseProductItem)

URL = reverse("operating:storefront_stock_items")


class StorefrontStock(TestCase):
    def setUp(self):
        laleli = Book.objects.create(name="Laleli Fabric")
        ergene = Book.objects.create(name="Ergene Fabric")
        self.shop = Warehouse.objects.create(
            name="Laleli", location="Gümrük Emini Sok. No 20, Fatih",
            public_name="Istanbul, Türkiye", accounting_book=laleli, on_storefront=True)
        self.factory = Warehouse.objects.create(name="Ergene Fabrika", accounting_book=ergene,
                                                on_storefront=True)
        self.abroad = Warehouse.objects.create(
            name="Almaty", accounting_book=Book.objects.create(name="Almaty"))

        cloth = Product.objects.create(title="2086", sku="2086", featured=False)
        variant = ProductVariant.objects.create(product=cloth, variant_sku="2086.WHITE")
        self.rolls = {}
        for warehouse, barcode, meters, lot in [
                (self.shop, "R1", "48.5", "4471"),
                (self.factory, "R2", "52", "4471"),
                (self.factory, "R3", "30", "4502"),
                (self.abroad, "R4", "60", "4471")]:
            row, _ = WarehouseProduct.objects.get_or_create(
                warehouse=warehouse, sku="2086.WHITE",
                defaults={"name": "2086 white", "catalog_variant": variant})
            self.rolls[barcode] = WarehouseProductItem.objects.create(
                product=row, barcode=barcode, quantity=Decimal(meters),
                quantity_remaining=Decimal(meters), lot_number=lot, status="in_stock")

        duvet = Product.objects.create(title="Duvet set", featured=False, unit="piece",
                                       pack_type="loose", tracking="variant")
        duvet_variant = ProductVariant.objects.create(product=duvet, variant_sku="DUV.160")
        for warehouse, count in [(self.shop, 3), (self.shop, 5), (self.factory, 4)]:
            row, _ = WarehouseProduct.objects.get_or_create(
                warehouse=warehouse, sku="DUV.160",
                defaults={"name": "Duvet set", "catalog_variant": duvet_variant})
            WarehouseProductItem.objects.create(
                product=row, quantity=Decimal(count), quantity_remaining=Decimal(count),
                status="in_stock")

        self.buyer = WebClient.objects.create(
            username="buyer", email="buyer@example.com", name="Buyer",
            password=make_password("pw"), is_active=True)

    def get(self, sku, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.get(URL, {"sku": sku}, **headers)

    def signed_in(self, sku):
        response = self.get(sku, issue(self.buyer))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_only_a_signed_in_customer_sees_the_stock(self):
        for token in (None, "forged"):
            with self.subTest(token=token):
                self.assertEqual(self.get("2086.WHITE", token).status_code, 401)

    def test_cloth_is_offered_roll_by_roll_with_lot_and_place(self):
        data = self.signed_in("2086.WHITE")
        self.assertEqual(data["tracking"], "item")
        self.assertEqual(data["unit"], "m")
        self.assertEqual(
            [(i["id"], i["available"], i["lot"], i["location"]) for i in data["items"]],
            [(self.rolls["R1"].pk, 48.5, "4471", "Istanbul, Türkiye"),
             (self.rolls["R2"].pk, 52.0, "4471", "Ergene Fabrika"),
             (self.rolls["R3"].pk, 30.0, "4502", "Ergene Fabrika")])
        self.assertEqual(data["locations"],
                         [{"location": "Istanbul, Türkiye", "available": 48.5},
                          {"location": "Ergene Fabrika", "available": 82.0}])

    def test_a_blank_public_name_falls_back_to_the_warehouse_name(self):
        self.assertEqual(self.factory.shown_as, "Ergene Fabrika")
        self.shop.public_name = "  "
        self.assertEqual(self.shop.shown_as, "Laleli")

    def test_what_other_orders_hold_is_not_offered(self):
        order = Order.objects.create(order_number="900")
        roll = self.rolls["R2"]
        OrderStockReservation.objects.create(
            order=order, stock_item=roll, warehouse_product=roll.product,
            quantity=Decimal("52"))
        OrderStockReservation.objects.create(
            order=order, stock_item=self.rolls["R3"],
            warehouse_product=self.rolls["R3"].product, quantity=Decimal("10"))
        data = self.signed_in("2086.WHITE")
        self.assertEqual([(i["id"], i["available"]) for i in data["items"]],
                         [(self.rolls["R1"].pk, 48.5), (self.rolls["R3"].pk, 20.0)])

    def test_nothing_internal_is_sent(self):
        body = self.get("2086.WHITE", issue(self.buyer)).content.decode()
        for secret in ("R1", "Gümrük", "Laleli Fabric", "Ergene Fabric\"", "cost", "book"):
            self.assertNotIn(secret, body)

    def test_ready_made_goods_are_a_quantity_per_place(self):
        data = self.signed_in("DUV.160")
        self.assertEqual(data["tracking"], "variant")
        self.assertEqual(data["unit"], "piece")
        self.assertEqual(data["items"], [])
        self.assertEqual(data["locations"],
                         [{"location": "Istanbul, Türkiye", "available": 8.0},
                          {"location": "Ergene Fabrika", "available": 4.0}])

    def test_a_sku_with_nothing_free_offers_nothing(self):
        self.assertEqual(self.signed_in("NOPE")["locations"], [])

    def test_a_warehouse_off_the_storefront_is_not_offered(self):
        """Almaty's roll of the same lot is not in the list: a buyer of the
        site can't be sent it."""
        data = self.signed_in("2086.WHITE")
        self.assertNotIn(self.rolls["R4"].pk, [i["id"] for i in data["items"]])
        self.assertNotIn("Almaty", [p["location"] for p in data["locations"]])

    def test_a_new_warehouse_starts_off_the_storefront(self):
        self.assertFalse(self.abroad.on_storefront)
        admin = get_user_model().objects.create_superuser("boss", "b@t.com", "pw")
        self.client.force_login(admin)
        self.client.post(reverse("operating:create_warehouse"), {
            "name": "Depo 2", "kind": "normal",
            "accounting_book": str(self.factory.accounting_book_id),
        })
        self.assertFalse(Warehouse.objects.get(name="Depo 2").on_storefront)

    def test_the_warehouse_form_saves_both(self):
        admin = get_user_model().objects.create_superuser("boss", "b@t.com", "pw")
        self.client.force_login(admin)
        form = {"name": "Ergene Fabrika", "kind": "normal",
                "accounting_book": str(self.factory.accounting_book_id),
                "public_name": " Tekirdağ, Türkiye "}
        page = self.client.get(reverse("operating:warehouse_edit", args=[self.factory.pk]))
        self.assertContains(page, 'name="on_storefront"')
        self.client.post(reverse("operating:warehouse_edit", args=[self.factory.pk]),
                         {**form, "on_storefront": "on"})
        self.factory.refresh_from_db()
        self.assertEqual((self.factory.public_name, self.factory.on_storefront),
                         ("Tekirdağ, Türkiye", True))
        # An unticked box posts nothing: that is "off".
        self.client.post(reverse("operating:warehouse_edit", args=[self.factory.pk]), form)
        self.factory.refresh_from_db()
        self.assertFalse(self.factory.on_storefront)

    def test_the_warehouses_that_exist_stay_on(self):
        import importlib
        from django.apps import apps
        importlib.import_module(
            "operating.migrations.0115_warehouses_stay_on_the_storefront").switch_on(apps, None)
        self.assertEqual(set(Warehouse.objects.values_list("on_storefront", flat=True)), {True})
