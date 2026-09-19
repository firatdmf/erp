# to run this test, use the command:
# python manage.py test marketing.tests.test_variant_attribute_order

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import (
    Product, ProductVariant, ProductVariantAttribute, ProductVariantAttributeValue,
)


class VariantAttributeOrderTest(TestCase):
    """Every variant lists its attributes in the same sequence.

    They used to come back in whatever order the through table happened to
    return, so one row on the product page read "Color / Width" and the
    next "Width / Color" — the two columns nobody could scan down.
    """

    def setUp(self):
        self.color = ProductVariantAttribute.objects.create(name="color")
        self.width = ProductVariantAttribute.objects.create(name="width")
        self.product = Product.objects.create(title="Baklava")
        # Added width-first here and color-first there: the order the values
        # are attached in must not reach the page.
        self.first = self._variant("S-BAKLAVA.ECRU-305", [(self.width, "305"), (self.color, "ecru")])
        self.second = self._variant("S-BAKLAVA.GRAY-300", [(self.color, "gray"), (self.width, "300")])

        self.user = get_user_model().objects.create_superuser(
            username="attr_reader", password="pw", email="a@a.c")
        self.client.force_login(self.user)

    def _variant(self, sku, pairs):
        variant = ProductVariant.objects.create(product=self.product, variant_sku=sku)
        for attribute, value in pairs:
            variant.product_variant_attribute_values.add(
                ProductVariantAttributeValue.objects.create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=value,
                )
            )
        return variant

    def _names(self, variant):
        return [v.product_variant_attribute.name
                for v in variant.product_variant_attribute_values.all()]

    def test_attributes_come_back_sorted_by_name(self):
        self.assertEqual(self._names(self.first), ["color", "width"])
        self.assertEqual(self._names(self.second), ["color", "width"])

    def test_the_product_page_reads_the_same_way_down_every_row(self):
        html = self.client.get(
            reverse("marketing:product_detail", args=[self.product.pk])).content.decode()
        for sku in ("S-BAKLAVA.ECRU-305", "S-BAKLAVA.GRAY-300"):
            row = html.index(sku)
            self.assertLess(html.index("Color:", row), html.index("Width:", row),
                            f"{sku} lists its attributes the other way round")

    def test_the_names_a_variant_is_summarised_by_follow_the_same_order(self):
        self.assertEqual(self.second.attribute_summary(), "color: gray, width: 300")
        self.assertTrue(self.second.full_name.endswith("Color: gray / Width: 300"))
