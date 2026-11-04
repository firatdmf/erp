# to run this test, use the command:
# python manage.py test operating.tests.test_order_photo_viewer

"""On an order line the photo opens the photo viewer the warehouse uses,
with the photos and videos the storefront shows for the line's variant, in
the storefront's order; only the name opens the product.

The photo and the name were one link, as wide as the cell, so a click
anywhere beside the name — or on the photo, to see it bigger — left the
order for the product page.
"""
import html as html_lib
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import (
    Product, ProductFile, ProductVariant, ProductVariantAttribute,
    ProductVariantAttributeValue,
)
from operating.models import Order, OrderItem


class OrderPhotoViewerTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            title="Ready Made Curtain", sku="RMC", featured=False)
        self.variant = variant = ProductVariant.objects.create(
            product=self.product, variant_sku="RMC-CGR")
        variant.product_variant_attribute_values.add(
            ProductVariantAttributeValue.objects.create(
                product_variant_attribute=ProductVariantAttribute.objects.create(name="color"),
                product_variant_attribute_value="cactus green"))
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-363", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(current_account=account)
        OrderItem.objects.create(order=self.order, product=self.product,
                                 product_variant=variant,
                                 quantity=Decimal("1"), price=Decimal("10"))
        user = get_user_model().objects.create_superuser("firat_photo", "a@b.c", "pw")
        user.member.books.add(book)
        user.member.default_book = book
        user.member.save()
        self.client.force_login(user)

    def _page(self):
        resp = self.client.get(reverse("operating:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def _viewer(self, page):
        marker = 'class="od-prod-zoom" data-photos="'
        start = page.index(marker) + len(marker)
        return json.loads(html_lib.unescape(page[start:page.index('"', start)]))

    def _file(self, url, sequence, kind="image", variant=False, poster=None):
        return ProductFile.objects.create(
            product=None if variant else self.product,
            product_variant=self.variant if variant else None,
            file_url=url, file_type=kind, sequence=sequence, video_thumbnail=poster)

    def test_the_viewer_follows_the_storefront_first_photo_then_videos_then_the_rest(self):
        self._file("https://cdn.test/b.avif", 2)
        self._file("https://cdn.test/clip.mp4", 3, kind="video", poster="https://cdn.test/clip.jpg")
        self._file("https://cdn.test/a.avif", 1)
        page = self._page()
        self.assertIn('id="whPhotos"', page)
        self.assertIn('<img class="od-prod-img" src="https://cdn.test/a.avif"', page)
        self.assertEqual(self._viewer(page), [
            {"src": "https://cdn.test/a.avif", "alt": ""},
            {"src": "https://cdn.test/clip.mp4", "alt": "", "video": True,
             "poster": "https://cdn.test/clip.jpg"},
            {"src": "https://cdn.test/b.avif", "alt": ""},
        ])

    def test_the_lines_variant_shows_its_own_photos_as_on_the_storefront(self):
        self._file("https://cdn.test/product.avif", 0)
        self._file("https://cdn.test/green-2.avif", 2, variant=True)
        self._file("https://cdn.test/green-1.avif", 1, variant=True)
        self.assertEqual([p["src"] for p in self._viewer(self._page())],
                         ["https://cdn.test/green-1.avif", "https://cdn.test/green-2.avif"])

    def test_a_variant_with_no_photo_of_its_own_shows_the_products(self):
        self._file("https://cdn.test/product.avif", 0)
        self.assertEqual([p["src"] for p in self._viewer(self._page())],
                         ["https://cdn.test/product.avif"])

    def test_only_the_name_links_to_the_product(self):
        ProductFile.objects.create(product=self.product, file_url="https://cdn.test/a.avif")
        page = self._page()
        product_url = reverse("marketing:product_detail", kwargs={"pk": self.product.pk})
        link = f'<a href="{product_url}" class="od-prod-link"><span class="od-prod-title">Ready Made Curtain</span></a>'
        self.assertIn(link, page)
        self.assertEqual(page.count(f'href="{product_url}" class="od-prod-link"'), 1)
