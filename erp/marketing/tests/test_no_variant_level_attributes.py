# to run this test, use the command:
# python manage.py test marketing.tests.test_no_variant_level_attributes

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from marketing.models import Product, ProductAttribute, ProductVariant


class VariantsHaveNoAttributesOfTheirOwn(TestCase):
    """What tells one variant from another is its option values (color,
    width, header…); what the product is made of, its attributes, belongs
    to the product. Variants used to carry their own copy of the product's
    attributes too, from an Attributes column in the variant table: 636 of
    706 such rows on prod repeated the product's, 39 contradicted the
    variant's own width (C120). The column and its pop-up are gone.
    """

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(
            username="owner_va", password="pw"))
        self.product = Product.objects.create(title="RN1337", sku="RN1337")
        ProductVariant.objects.create(product=self.product, variant_sku="RN1337.GW8")
        ProductAttribute.objects.create(product=self.product, name="warranty", value="2")

    def test_the_variant_table_has_no_attributes_pop_up(self):
        page = self.client.get(reverse("marketing:product_edit", args=[self.product.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "variant_attributes_modal.js")
        # The product's own attributes are still edited on the page.
        self.assertContains(page, 'id="product_attributes_section"')

    def test_the_pop_ups_endpoint_is_gone(self):
        with self.assertRaises(NoReverseMatch):
            reverse("marketing:get_product_attributes")
