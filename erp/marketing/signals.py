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


# ------ below is when we do bulk deletion, we still delete the CDN file (Bunny or Cloudinary)
from django.db.models.signals import pre_delete


@receiver(pre_delete, sender=ProductFile)
def delete_cdn_file(sender, instance, **kwargs):
    product = instance.product
    if product and product.primary_image_id == instance.pk:
        product.primary_image = None
        product.save(update_fields=["primary_image"])

    # CRITICAL: Virtual Sharing protection
    # Before deleting from CDN, check if ANY other ProductFile still references the same URL.
    # If yes, skip CDN delete (another record still needs it).
    if instance.file_url:
        other_refs = ProductFile.objects.filter(file_url=instance.file_url).exclude(pk=instance.pk).exists()
        if other_refs:
            print(f"[SIGNAL] Skipping CDN delete — other ProductFile(s) still reference: {instance.file_url}")
        else:
            try:
                from .views import smart_delete
                print(f"[SIGNAL] delete_cdn_file triggered (last reference) for: {instance.file_url}")
                result = smart_delete(instance.file_url)
                print(f"[SIGNAL] smart_delete result: {result}")
            except Exception as e:
                print(f"[SIGNAL] Failed to delete CDN file {instance.file_url}: {e}")

    # Same protection for video thumbnail
    if instance.video_thumbnail:
        other_thumb_refs = ProductFile.objects.filter(video_thumbnail=instance.video_thumbnail).exclude(pk=instance.pk).exists()
        if other_thumb_refs:
            print(f"[SIGNAL] Skipping thumbnail delete — other refs exist: {instance.video_thumbnail}")
        else:
            try:
                from .views import smart_delete
                print(f"[SIGNAL] Deleting video thumbnail: {instance.video_thumbnail}")
                smart_delete(instance.video_thumbnail)
            except Exception as e:
                print(f"[SIGNAL] Failed to delete video thumbnail: {e}")
