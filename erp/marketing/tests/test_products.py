"""What a catalogue product and its variants must carry to be valid.

These tests used to describe a `has_variants` flag: a product either had
variants and no SKU or price of its own, or had no variants and needed a
SKU. The flag was dropped in 2db48afa and the `Product.clean()` enforcing
it was commented out in 628f32a0, so the two tests about that split went
with it — there is no longer a kind of product that may not have a SKU,
or may not take variants.

A third test asserted that a negative price fails validation. Neither
`Product.price` nor `ProductVariant.variant_price` has ever carried a
validator, so it had never passed; it is gone rather than kept failing.

What is left is what the models actually enforce: every product and every
variant needs a SKU, and no two may share one.

Run with:
    python manage.py test marketing.tests.test_products
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from marketing.models import Product, ProductCategory, ProductVariant


class AProductNeedsItsOwnSku(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Test Category")

    def test_a_product_with_a_sku_and_price_is_valid(self):
        product = Product(title="Simple Product", sku="SIMP123",
                          price=Decimal("9.99"), category=self.category)
        product.full_clean()

    def test_a_product_without_a_sku_is_not(self):
        product = Product(title="No SKU", sku="", category=self.category)
        with self.assertRaises(ValidationError) as caught:
            product.full_clean()
        self.assertIn("sku", caught.exception.message_dict)

    def test_two_products_cannot_share_a_sku(self):
        Product.objects.create(title="First", sku="DUP1", category=self.category)
        with self.assertRaises(ValidationError) as caught:
            Product(title="Second", sku="DUP1", category=self.category).full_clean()
        self.assertIn("sku", caught.exception.message_dict)


class AVariantNeedsItsOwnSku(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(name="Test Category")
        self.product = Product.objects.create(
            title="Product with Variants", sku="PARENT1", category=category)

    def test_a_variant_with_a_sku_and_price_is_valid(self):
        variant = ProductVariant(product=self.product, variant_sku="VARIANT001",
                                 variant_price=Decimal("10.00"))
        variant.full_clean()

    def test_a_variant_without_a_sku_is_not(self):
        variant = ProductVariant(product=self.product, variant_sku="")
        with self.assertRaises(ValidationError) as caught:
            variant.full_clean()
        self.assertIn("variant_sku", caught.exception.message_dict)

    def test_two_variants_cannot_share_a_sku(self):
        ProductVariant.objects.create(product=self.product, variant_sku="VDUP")
        with self.assertRaises(ValidationError) as caught:
            ProductVariant(product=self.product, variant_sku="VDUP").full_clean()
        self.assertIn("variant_sku", caught.exception.message_dict)
