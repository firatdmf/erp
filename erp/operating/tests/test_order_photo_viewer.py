# to run this test, use the command:
# python manage.py test operating.tests.test_order_photo_viewer

"""On an order line the photo opens the photo viewer the warehouse uses,
and only the name opens the product.

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
        variant = ProductVariant.objects.create(product=self.product, variant_sku="RMC-CGR")
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

    def test_the_photo_opens_every_photo_of_the_product_in_the_viewer(self):
        for url, kind in (("https://cdn.test/a.avif", "image"),
                          ("https://cdn.test/clip.mp4", "video"),
                          ("https://cdn.test/b.avif", "image")):
            ProductFile.objects.create(product=self.product, file_url=url, file_type=kind)
        page = self._page()
        self.assertIn('id="whPhotos"', page)
        start = page.index('class="od-prod-zoom" data-photos="') + len('class="od-prod-zoom" data-photos="')
        photos = json.loads(html_lib.unescape(page[start:page.index('"', start)]))
        self.assertEqual([p["src"] for p in photos],
                         ["https://cdn.test/a.avif", "https://cdn.test/b.avif"])

    def test_only_the_name_links_to_the_product(self):
        ProductFile.objects.create(product=self.product, file_url="https://cdn.test/a.avif")
        page = self._page()
        product_url = reverse("marketing:product_detail", kwargs={"pk": self.product.pk})
        link = f'<a href="{product_url}" class="od-prod-link"><span class="od-prod-title">Ready Made Curtain</span></a>'
        self.assertIn(link, page)
        self.assertEqual(page.count(f'href="{product_url}" class="od-prod-link"'), 1)
