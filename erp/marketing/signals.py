from django.db.models.signals import post_save, pre_save
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


# ------ A variant SKU rename has to reach the paperwork that quotes it.
# An invoice line's text is a snapshot taken when the line was cut and it
# embeds the SKU ("… — g77 [K24861T.G77]"), so renaming the variant used to
# leave every existing document printing the dead code. pre_save reads the
# stored SKU — only when that column is actually in play, so an ordinary
# variant save costs no extra query — and post_save re-renders the lines.
@receiver(pre_save, sender=ProductVariant)
def stash_old_variant_sku(sender, instance, **kwargs):
    instance._old_variant_sku = None
    if not instance.pk:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "variant_sku" not in update_fields:
        return
    instance._old_variant_sku = (
        ProductVariant.objects.filter(pk=instance.pk)
        .values_list("variant_sku", flat=True).first()
    )


@receiver(post_save, sender=ProductVariant)
def propagate_variant_sku_rename(sender, instance, created, **kwargs):
    old = getattr(instance, "_old_variant_sku", None)
    instance._old_variant_sku = None
    if created or not old or old == instance.variant_sku:
        return
    try:
        from accounting.services_accounts import refresh_invoice_lines_for_variant
        updated, skipped = refresh_invoice_lines_for_variant(instance)
    except Exception:
        # Renaming the variant is already committed; a document that could
        # not be re-rendered must never turn that into a failed save.
        import traceback
        print(f"[SIGNAL] Failed to re-render invoice lines for {instance.variant_sku}:")
        traceback.print_exc()
        return
    if updated or skipped:
        msg = f"[SIGNAL] {old} → {instance.variant_sku}: {updated} invoice line(s) re-rendered"
        if skipped:
            msg += f"; e-Arşiv filed invoice(s) left untouched: {skipped}"
        print(msg)


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
