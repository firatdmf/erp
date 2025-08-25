from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductFile,
)


# I want to ensure that we do not save a product variant unless we are also saving it's attribute and attribute value.
# @receiver(post_save, sender=ProductVariant)
# def ensure_product_variant_attributes_values(sender, instance, created, **kwargs):
#     if created:
#         attributes = ProductVariantAttribute.objects.all()
#         for attribute in attributes:
#             ProductVariantAttributeValue.objects.get_or_create(
#                 product_variant_attribute=attribute,
#                 defaults={"product_variant_attribute_value": "Default Value"},
#             )

@receiver(post_save, sender=ProductFile)
def set_primary_image_on_first_upload(sender, instance, created, **kwargs):
    # Only for main product images (not variant images)
    if created and instance.product:
        product = instance.product
        if not product.primary_image:
            product.primary_image = instance
            product.save(update_fields=["primary_image"])



# ------ below is when we do bulk deletion, we still delete the cloudinary image
from django.db.models.signals import pre_delete
from cloudinary.uploader import destroy as cloudinary_destroy
import re

@receiver(pre_delete, sender=ProductFile)
def delete_cloudinary_file(sender, instance, **kwargs):
    if instance.file_url:
        match = re.search(r"/upload/(?:v\d+/)?([^\.]+)", instance.file_url)
        if match:
            public_id = match.group(1)
            try:
                cloudinary_destroy(public_id)
            except Exception as e:
                print(f"Failed to delete Cloudinary resource {public_id}: {e}")