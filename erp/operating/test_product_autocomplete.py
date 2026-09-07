# to run this test, use the command:
# python manage.py test operating.test_product_autocomplete

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import (Product, ProductVariant,
                             ProductVariantAttribute,
                             ProductVariantAttributeValue)
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
        # A warehouse states which book owns its stock; the picker
        # only searches the shelves of books the viewer works in.
        self.warehouse = Warehouse.objects.create(
            name="Fabrika",
            accounting_book=Book.objects.create(name="Laleli Fabric"))
        self.product = Product.objects.create(
            title="PETEK FONLUK KUMAŞ", sku="PETEK FONLUK", featured=False)

    def _stock(self, colour):
        sku = f"PETEK.FONLUK KUMAŞ.{colour}.310"
        v = ProductVariant.objects.create(
            product=self.product, variant_sku=sku)
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
        from operating.models import Order, OrderStockReservation, WarehouseProductItem
        self.OrderStockReservation = OrderStockReservation
        self.user = get_user_model().objects.create_superuser(
            username="free_stock", password="pw", email="f@s.t")
        self.client.force_login(self.user)
        # A warehouse states which book owns its stock; the picker
        # only searches the shelves of books the viewer works in.
        self.warehouse = Warehouse.objects.create(
            name="Fabrika",
            accounting_book=Book.objects.create(name="Laleli Fabric"))
        product = Product.objects.create(title="PETEK", sku="PETEK-T", featured=False)
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="PETEK.94.310")
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="PETEK FONLUK KUMAŞ 94",
            sku="PETEK.94.310", quantity=Decimal("30"), catalog_variant=self.variant)
        self.stock_item = WarehouseProductItem.objects.create(
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
        self.OrderStockReservation.objects.create(
            order=self.order, stock_item=self.stock_item, warehouse_product=self.wp,
            meters=Decimal("30"), consumed=False)
        self.assertIn("0", self._stock_shown())
        self.assertNotIn("30", self._stock_shown())

    def test_a_partial_reservation_leaves_the_remainder(self):
        self.OrderStockReservation.objects.create(
            order=self.order, stock_item=self.stock_item, warehouse_product=self.wp,
            meters=Decimal("12"), consumed=False)
        self.assertIn("18", self._stock_shown())


class WarehouseFirstCatalogOnDemandTest(TestCase):
    """The list answers "what can I ship" first.

    Warehouse and catalog rows used to be interleaved and styled by two
    separate renderers, so the same product appeared under different
    names with differently-shaped badges. Catalog rows are now grouped
    behind a click, and every row — whichever source — goes through one
    skeleton.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="wh_first", password="pw", email="w@f.t")
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Laleli Fabric")
        self.warehouse = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=self.book)

        # On a shelf.
        self.stocked = Product.objects.create(
            title="ARDEN", sku="ARDEN", featured=False, price=Decimal("9.00"))
        v = ProductVariant.objects.create(
            product=self.stocked, variant_sku="ARDEN.G10")
        WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="ARDEN ALTIN", sku="ARDEN.G10",
            quantity=Decimal("40"), catalog_variant=v)

        # In the catalog only — no warehouse row anywhere.
        self.shelfless = Product.objects.create(
            title="ARDEN PERDE", sku="ARDEN-P", featured=False,
            price=Decimal("11.00"))

    def _search(self, q="ARDEN"):
        return self.client.get(reverse("operating:product_autocomplete"),
                               {"product": q, "book": self.book.pk}).content.decode()

    def test_a_catalog_row_waits_behind_a_click(self):
        html = self._search()
        self.assertIn("pa-more", html)
        # Rendered, but closed — the expander is a class toggle, not a
        # second round-trip on a keystroke-driven search.
        self.assertIn("ARDEN PERDE", html)
        self.assertIn("pa-catalog", html)

    def test_a_warehouse_row_is_never_hidden(self):
        html = self._search()
        row = [ln for ln in html.split("<li ") if "ARDEN.G10" in ln][0]
        self.assertNotIn("pa-catalog", row)

    def test_catalog_opens_straight_away_when_nothing_is_stocked(self):
        """With no warehouse answer there is nothing to defer TO —
        collapsing would show a list whose every row is hidden."""
        html = self._search("PERDE")
        self.assertIn("ARDEN PERDE", html)
        self.assertNotIn("pa-more", html)
        self.assertNotIn("pa-catalog", html)

    def test_every_row_uses_the_one_skeleton(self):
        html = self._search()
        self.assertEqual(html.count("pa-main"), html.count("pa-row"))
        self.assertEqual(html.count("pa-meta"), html.count("pa-row"))

    def test_a_cost_fallback_says_so_in_words(self):
        """Amber alone is invisible to anyone not hovering, and a rep
        reading this list was quoting purchase cost as a sale price."""
        self.shelfless.price = None
        self.shelfless.cost = Decimal("4.25")
        self.shelfless.save()
        html = self._search("PERDE")
        self.assertIn("pa-price--cost", html)
        self.assertIn("Cost", html)

    def test_a_real_price_is_not_labelled_a_cost(self):
        html = self._search("PERDE")
        self.assertNotIn("pa-price--cost", html)

    def test_attribute_values_are_not_shown_slugged(self):
        """Values are stored slugged and lowercase (`light_cream`)."""
        attr = ProductVariantAttribute.objects.create(name="model")
        value = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attr,
            product_variant_attribute_value="nevresim_takimi")
        variant = ProductVariant.objects.create(
            product=self.shelfless, variant_sku="ARDEN-P.1")
        variant.product_variant_attribute_values.add(value)
        html = self._search("ARDEN-P.1")
        # The attribute NAME comes too: "nevresim takimi" alone reads as
        # a product, and a bare "yes" or "g54" says nothing at all.
        self.assertIn("model: nevresim takimi", html)
        self.assertNotIn("nevresim_takimi", html)

    def test_the_search_does_not_scale_its_queries_with_its_rows(self):
        for i in range(12):
            v = ProductVariant.objects.create(
                product=self.stocked, variant_sku=f"ARDEN.G{20 + i}")
            WarehouseProduct.objects.create(
                warehouse=self.warehouse, name=f"ARDEN {i}",
                sku=f"ARDEN.G{20 + i}", quantity=Decimal("5"),
                catalog_variant=v)
        with self.assertNumQueries(self.baseline_queries()):
            self._search()

    def baseline_queries(self):
        """Measured on the small fixture, asserted on the large one: the
        prefetches make the count independent of how many rows come back,
        which is the property worth pinning."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            self._search()
        return len(ctx)
