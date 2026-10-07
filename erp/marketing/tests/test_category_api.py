"""The storefront draws a card for every product group the API hands it."""
from django.test import TestCase
from django.urls import reverse

from marketing.models import ProductCategory


class TheStorefrontsCategoryList(TestCase):
    def test_a_group_switched_off_is_not_handed_to_the_storefront(self):
        ProductCategory.objects.create(name="bed")
        ProductCategory.objects.create(name="bath", is_active=False)
        response = self.client.get(reverse("marketing:get_product_categories"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["name"] for c in response.json()], ["bed"])
