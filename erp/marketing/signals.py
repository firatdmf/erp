from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
)


# I want to ensure that we do not save a product variant unless we are also saving it's attribute and attribute value.


@receiver(post_save, sender=ProductVariant)
def ensure_product_variant_attributes_values(sender, instance, created, **kwargs):
    if created:
        attributes = ProductVariantAttribute.objects.all()
        for attribute in attributes:
            ProductVariantAttributeValue.objects.get_or_create(
                variant=instance,
                attribute=attribute,
                defaults={"value": "Default Value"},
            )
