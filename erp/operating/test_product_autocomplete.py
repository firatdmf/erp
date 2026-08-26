# to run this test, use the command:
# python manage.py test operating.test_product_autocomplete

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import Product, ProductVariant
from operating.models import Warehouse, WarehouseProduct


class ProductAutocompleteBreadthTest(TestCase):
    """The order screen's product search must not hide matches silently.

    It rendered the first 8 warehouse rows and stopped. Searching "PETEK"
    returned 13, so seven colours of one fabric appeared and the eighth —
    PETEK.FONLUK KUMAŞ.95.310, ninth in name order — simply wasn't there,
    with nothing on screen to say the list had been cut.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="ac_tester", password="pw", email="a@c.t")
        self.client.force_login(self.user)
        self.warehouse = Warehouse.objects.create(name="Fabrika")
        self.product = Product.objects.create(
            title="PETEK FONLUK KUMAŞ", sku="PETEK FONLUK", featured=False)

    def _stock(self, colour):
        sku = f"PETEK.FONLUK KUMAŞ.{colour}.310"
        v = ProductVariant.objects.create(
            product=self.product, variant_sku=sku, variant_quantity=Decimal("30"))
        WarehouseProduct.objects.create(
            warehouse=self.warehouse, name=f"PETEK FONLUK KUMAŞ {colour}",
            sku=sku, quantity=Decimal("30"), catalog_variant=v)
        return sku

    def _search(self, q):
        return self.client.get(reverse("operating:product_autocomplete"),
                               {"product": q}).content.decode()

    def test_every_colour_of_one_fabric_is_listed(self):
        skus = [self._stock(c) for c in
                ("193", "200", "209", "224", "248", "340", "590", "94", "95")]
        html = self._search("PETEK")
        missing = [s for s in skus if s not in html]
        self.assertEqual(missing, [], f"hidden from the search: {missing}")

    def test_a_truncated_list_says_so(self):
        """Beyond the cap the user is told, rather than left to assume the
        rest doesn't exist."""
        for i in range(25):
            self._stock(f"{100 + i}")
        html = self._search("PETEK")
        self.assertIn("more in the warehouse", html)


class AutocompleteOffersOnlyFreeStockTest(TestCase):
    """Metres already reserved into another order are spoken for.

    The list showed what was on the shelf, so a roll fully reserved for one
    order still advertised its full length to the next — which is how the
    same roll gets promised twice.
    """

    def setUp(self):
        from operating.models import Order, OrderRollReservation, WarehouseProductRoll
        self.OrderRollReservation = OrderRollReservation
        self.user = get_user_model().objects.create_superuser(
            username="free_stock", password="pw", email="f@s.t")
        self.client.force_login(self.user)
        self.warehouse = Warehouse.objects.create(name="Fabrika")
        product = Product.objects.create(title="PETEK", sku="PETEK-T", featured=False)
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="PETEK.94.310", variant_quantity=Decimal("30"))
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="PETEK FONLUK KUMAŞ 94",
            sku="PETEK.94.310", quantity=Decimal("30"), catalog_variant=self.variant)
        self.roll = WarehouseProductRoll.objects.create(
            product=self.wp, meters=Decimal("30"), barcode="PTK-1")
        self.order = Order.objects.create()

    def _stock_shown(self):
        html = self.client.get(reverse("operating:product_autocomplete"),
                               {"product": "PETEK FONLUK"}).content.decode()
        import re
        return re.findall(r"([\d.]+) m</span>", html)

    def test_unreserved_stock_is_offered_in_full(self):
        self.assertIn("30", self._stock_shown())

    def test_reserved_metres_are_not_offered(self):
        self.OrderRollReservation.objects.create(
            order=self.order, roll=self.roll, warehouse_product=self.wp,
            meters=Decimal("30"), consumed=False)
        self.assertIn("0", self._stock_shown())
        self.assertNotIn("30", self._stock_shown())

    def test_a_partial_reservation_leaves_the_remainder(self):
        self.OrderRollReservation.objects.create(
            order=self.order, roll=self.roll, warehouse_product=self.wp,
            meters=Decimal("12"), consumed=False)
        self.assertIn("18", self._stock_shown())
