"""A product group chooses which of its attributes the storefront's listing
filters by; the products API hands that list to the storefront."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import (CategoryVariantAttribute, Product, ProductCategory,
                              ProductVariant, ProductVariantAttribute)


class StorefrontFiltersTest(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(
            username="filters", password="pw", email="f@i.l"))
        self.group = ProductCategory.objects.create(name="fabric", price_multiplier="4/3")

    def _save(self, attributes, filters):
        return self.client.post(
            reverse("marketing:product_group_detail", args=[self.group.pk]),
            {"action": "save_settings", "name": "fabric", "price_multiplier": "4/3",
             "variant_attributes_sent": "1", "variant_attributes": attributes,
             "storefront_filters": filters})

    def test_the_ticked_attributes_are_the_filters_in_the_groups_order(self):
        self.assertEqual(self._save(["color", "width", "embellishment"],
                                    ["embellishment", "color"]).status_code, 200)
        self.assertEqual(self.group.variant_attribute_names(), ["color", "width", "embellishment"])
        self.assertEqual(self.group.storefront_filter_names(), ["color", "embellishment"])

    def test_the_page_shows_the_ticks(self):
        self._save(["color", "width"], ["width"])
        html = self.client.get(reverse("marketing:product_group_detail",
                                       args=[self.group.pk])).content.decode()
        self.assertIn('name="storefront_filters" value="width" checked', html)
        self.assertNotIn('name="storefront_filters" value="color" checked', html)

    def test_the_products_api_hands_the_storefront_the_filters(self):
        attr = ProductVariantAttribute.objects.create(name="embellishment")
        CategoryVariantAttribute.objects.create(category=self.group, attribute=attr,
                                                storefront_filter=True)
        url = reverse("marketing:get_products") + "?product_category=fabric"
        # with no website products, and with one
        self.assertEqual(self.client.get(url).json()["filter_attributes"], ["embellishment"])
        product = Product.objects.create(title="N1306", sku="N1306", category=self.group,
                                         featured=True)
        ProductVariant.objects.create(product=product, variant_sku="N1306.G24-CRYSTAL")
        self.assertEqual(self.client.get(url).json()["filter_attributes"], ["embellishment"])
