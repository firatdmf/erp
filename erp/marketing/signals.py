from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductFile,
)


# I want to ensure that we do not save a product variant unless we are also saving it's attribute and attribute value.


@receiver(post_save, sender=ProductVariant)
def ensure_product_variant_attributes_values(sender, instance, created, **kwargs):
    if created:
        attributes = ProductVariantAttribute.objects.all()
        for attribute in attributes:
            ProductVariantAttributeValue.objects.get_or_create(
                product_variant=instance,
                product_variant_attribute=attribute,
                defaults={"product_variant_attribute_value": "Default Value"},
            )


@receiver(post_save, sender=ProductFile)
def set_primary_image_on_first_upload(sender, instance, created, **kwargs):
    # Only for main product images (not variant images)
    if created and instance.product:
        product = instance.product
        if not product.primary_image:
            product.primary_image = instance
            product.save(update_fields=["primary_image"])
