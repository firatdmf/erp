"""A product group's rule decides what the storefront shows.

"In stock, with a photo of its own" shows a variant while it has stock and a
photo attached to it, hides it otherwise, and shows its product while any
variant is shown; "With a photo of its own" asks for the photo alone. The
ticks are kept so as stock and photos change, so nobody has to tick and
untick a group whose shelves move every day.

Run with:
    python manage.py test marketing.tests.test_storefront_visibility
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing import storefront_visibility
from marketing.models import Product, ProductCategory, ProductFile, ProductVariant
from operating.models import Warehouse, WarehouseProduct

RULE = ProductCategory.STOREFRONT_IN_STOCK_WITH_PHOTO


class StorefrontRuleTest(TestCase):
    def setUp(self):
        self.group = ProductCategory.objects.create(name="fabric", price_multiplier="4/3",
                                                    storefront_rule=RULE)
        self.product = Product.objects.create(title="2052", sku="2052", category=self.group)
        self.shelf = Warehouse.objects.create(
            name="Laleli", accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0],
            on_storefront=True)

    def _variant(self, sku, stock=None, photo=False):
        with self.captureOnCommitCallbacks(execute=True):
            v = ProductVariant.objects.create(product=self.product, variant_sku=sku, variant_featured=False)
            if stock is not None:
                WarehouseProduct.objects.create(warehouse=self.shelf, name=sku, sku=sku,
                                                quantity=Decimal(stock), catalog_variant=v)
            if photo:
                ProductFile.objects.create(product=self.product, product_variant=v,
                                           file_url=f"https://cdn.example/{sku}.avif", file_type="image")
        v.refresh_from_db()
        return v

    def test_stock_and_a_photo_of_its_own_show_a_variant(self):
        self.assertTrue(self._variant("2052.GOLD_ECRU", stock="95.7", photo=True).variant_featured)
        self.product.refresh_from_db()
        self.assertTrue(self.product.featured)

    def test_no_photo_of_its_own_hides_it(self):
        ProductFile.objects.create(product=self.product, file_url="https://cdn.example/all.avif",
                                   file_type="image")  # the product's, not the variant's
        self.assertFalse(self._variant("2052.SILVER_ECRU", stock="302", photo=False).variant_featured)

    def test_no_stock_hides_it(self):
        self.assertFalse(self._variant("2052.GOLD_OFFWHITE", stock="0", photo=True).variant_featured)
        self.product.refresh_from_db()
        self.assertFalse(self.product.featured)

    def test_selling_out_hides_it_and_restocking_shows_it_again(self):
        v = self._variant("2052.GOLD_ECRU", stock="10", photo=True)
        row = v.warehouse_products.get()
        with self.captureOnCommitCallbacks(execute=True):
            row.quantity = Decimal("0")
            row.save()
        v.refresh_from_db()
        self.assertFalse(v.variant_featured)
        with self.captureOnCommitCallbacks(execute=True):
            row.quantity = Decimal("5")
            row.save()
        v.refresh_from_db()
        self.assertTrue(v.variant_featured)

    def test_stock_off_the_storefront_does_not_show_a_variant(self):
        self.shelf.on_storefront = False
        self.shelf.save()
        self.assertFalse(self._variant("2052.GOLD_ECRU", stock="95.7", photo=True).variant_featured)

    def test_switching_the_warehouse_on_shows_its_stock(self):
        self.shelf.on_storefront = False
        self.shelf.save()
        v = self._variant("2052.GOLD_ECRU", stock="95.7", photo=True)
        self.assertFalse(v.variant_featured)
        admin = get_user_model().objects.create_superuser("boss", "b@t.com", "pw")
        self.client.force_login(admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("operating:warehouse_edit", args=[self.shelf.pk]), {
                "name": "Laleli", "kind": "normal",
                "accounting_book": str(self.shelf.accounting_book_id),
                "on_storefront": "on",
            })
        v.refresh_from_db()
        self.assertTrue(v.variant_featured)

    def test_a_tick_by_hand_is_put_back_to_the_rule(self):
        v = self._variant("2052.SILVER_ECRU", stock="302")
        with self.captureOnCommitCallbacks(execute=True):
            v.variant_featured = True
            v.save()
        v.refresh_from_db()
        self.assertFalse(v.variant_featured)

    def test_photo_only_shows_a_variant_without_stock(self):
        self.group.storefront_rule = ProductCategory.STOREFRONT_WITH_PHOTO
        with self.captureOnCommitCallbacks(execute=True):
            self.group.save()
        sold_out = self._variant("ALBERT.GREY-200X220CM", stock="0", photo=True)
        bare = self._variant("B-LUCAS.WHITE-200X220CM", stock="40", photo=False)
        self.assertTrue(sold_out.variant_featured)
        self.assertFalse(bare.variant_featured)
        self.assertEqual(storefront_visibility.hidden_reasons(self.product),
                         {sold_out.pk: None, bare.pk: storefront_visibility.NO_PHOTO})

    def test_a_new_group_starts_on_stock_and_photo(self):
        self.assertEqual(ProductCategory.objects.create(name="towel", price_multiplier="4/3").storefront_rule, RULE)

    def test_the_reasons_say_why(self):
        a = self._variant("A", stock="0", photo=True)
        b = self._variant("B", stock="3", photo=False)
        c = self._variant("C", stock="3", photo=True)
        self.assertEqual(storefront_visibility.hidden_reasons(self.product),
                         {a.pk: storefront_visibility.NO_STOCK, b.pk: storefront_visibility.NO_PHOTO, c.pk: None})


class StorefrontScreensTest(TestCase):
    def setUp(self):
        group = ProductCategory.objects.create(name="fabric", price_multiplier="4/3", storefront_rule=RULE)
        self.shown = Product.objects.create(title="GREK", sku="GREK", category=group, featured=True)
        self.hidden = Product.objects.create(title="2052", sku="2052", category=group, featured=False)
        ProductVariant.objects.create(product=self.hidden, variant_sku="2052.SILVER_ECRU")
        user = get_user_model().objects.create_superuser("boss", password="pw")
        self.client.force_login(user)

    def test_the_list_filters_by_storefront(self):
        html = self.client.get(reverse("marketing:product_list"), {"storefront": "hidden"},
                               HTTP_HX_REQUEST="true").content.decode()
        self.assertIn("2052", html)
        self.assertNotIn(">GREK<", html)

    def test_the_product_page_says_why_a_variant_is_hidden(self):
        html = self.client.get(reverse("marketing:product_detail", args=[self.hidden.pk])).content.decode()
        self.assertIn("Hidden: no stock", html)
