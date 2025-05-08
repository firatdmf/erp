# This is built in django test framework
from django.test import TestCase
from marketing.models import Product, ProductVariant,ProductCategory
from django.core.exceptions import ValidationError
from decimal import Decimal

# to run this test, use the command:
# python manage.py test marketing.tests.test_products

class ProductModelTest(TestCase):

    def setUp(self):
        # Set up any initial data if needed
        self.category = ProductCategory.objects.create(name="Test Category")
    
    def test_product_with_variants_should_not_have_sku(self):
        # Creating a product with variants
        product = Product.objects.create(
            title="Product with Variants",
            has_variants=True,
            price=None,  # No price because it's a variant-based product
            sku="PROD123",  # This should trigger a validation error
            category=self.category
        )
        
        # Try to clean the product instance
        with self.assertRaises(ValidationError):
            product.full_clean()  # This will raise an error because SKU should be None for variant products
    
    def test_product_without_variants_should_require_sku(self):
        # Creating a simple product without variants
        product = Product.objects.create(
            title="Simple Product",
            has_variants=False,
            price=Decimal("9.99"),  # Price is required for simple products
            sku="SIMP123",  # This is required for simple products
            category=self.category
        )
        
        # Ensure this passes validation
        try:
            product.full_clean()  # This should pass as SKU is provided
        except ValidationError as e:
            self.fail(f"Validation failed unexpectedly: {e}")

    def test_variant_can_only_be_associated_with_products_that_allow_variants(self):
        # Creating a product that does NOT allow variants
        product = Product.objects.create(
            title="Product Without Variants",
            has_variants=False,
            price=Decimal("5.99"),
            sku="NO_VARIANT",
            category=self.category
        )
        
        # Try creating a variant for this product
        variant = ProductVariant(
            product=product,
            variant_sku="VARIANT123",
            variant_price=Decimal("5.00"),
            variant_quantity=Decimal("100.00")
        )
        
        # Try to clean the variant (it should fail because the product doesn't allow variants)
        with self.assertRaises(ValidationError):
            variant.full_clean()
    
    def test_variant_for_product_with_variants_should_be_valid(self):
        # Create a product that allows variants
        product = Product.objects.create(
            title="Product with Variants",
            has_variants=True,
            price=None,  # No price as variants will have individual prices
            sku=None,  # No SKU as variants will have individual SKUs
            category=self.category
        )

        # Create a valid variant for this product
        variant = ProductVariant(
            product=product,
            variant_sku="VARIANT001",
            variant_price=Decimal("10.00"),
            variant_quantity=Decimal("200.00")
        )

        try:
            variant.full_clean()  # This should pass as the product allows variants
        except ValidationError as e:
            self.fail(f"Validation failed unexpectedly: {e}")

    def test_product_with_invalid_price_should_raise_error(self):
        # Creating a product with an invalid price (e.g., negative)
        product = Product.objects.create(
            title="Product with Invalid Price",
            has_variants=False,
            price=Decimal("-5.99"),  # Invalid price
            sku="INVALIDPRICE",
            category=self.category
        )

        # Try to clean the product instance
        with self.assertRaises(ValidationError):
            product.full_clean()  # Should raise ValidationError for invalid price