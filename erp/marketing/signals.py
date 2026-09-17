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


# ------ Deleting a product takes its files off the CDN.
# pre_delete fires for every ProductFile however it goes — file.delete(), a
# queryset delete, or the cascade from its product or variant — so this is
# the one place that cleans up. The CDN call waits for the commit: a delete
# that rolls back must not leave the kept rows pointing at dead files. And
# it asks at that point whether anything still shows the URL, so a file
# shared with another product, a colour swatch or a group image stays, and
# two rows sharing a URL that go together still take it with them.
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import pre_delete


def cdn_url_in_use(url):
    from .models import ProductCategory, VariantAttributeValueImage
    return (
        ProductFile.objects.filter(Q(file_url=url) | Q(video_thumbnail=url)).exists()
        or VariantAttributeValueImage.objects.filter(image_url=url).exists()
        or ProductCategory.objects.filter(image_url=url).exists()
    )


def delete_from_cdn_after_commit(*urls):
    urls = {u for u in urls if u}
    if not urls:
        return

    def run():
        from .views import smart_delete
        for url in urls:
            if cdn_url_in_use(url):
                print(f"[SIGNAL] Keeping CDN file, still in use: {url}")
                continue
            try:
                print(f"[SIGNAL] Deleting CDN file: {url} → {smart_delete(url)}")
            except Exception as e:
                print(f"[SIGNAL] Failed to delete CDN file {url}: {e}")

    transaction.on_commit(run)


@receiver(pre_delete, sender=ProductFile)
def delete_cdn_file(sender, instance, **kwargs):
    product = instance.product
    if product and product.primary_image_id == instance.pk:
        product.primary_image = None
        product.save(update_fields=["primary_image"])
    if not getattr(instance, "_skip_cdn", False):
        delete_from_cdn_after_commit(instance.file_url, instance.video_thumbnail)


@receiver(pre_delete, sender="marketing.VariantAttributeValueImage")
def delete_swatch_cdn_file(sender, instance, **kwargs):
    delete_from_cdn_after_commit(instance.image_url)
