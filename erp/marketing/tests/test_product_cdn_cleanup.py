"""Deleting a product takes its files off the CDN.

Run with:
    python manage.py test marketing.tests.test_product_cdn_cleanup
"""
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase

from marketing.models import (
    Product, ProductCategory, ProductFile, ProductVariant,
    ProductVariantAttribute, ProductVariantAttributeValue,
    VariantAttributeValueImage,
)

CDN = "https://cdn.example/media/"


@patch("marketing.views.smart_delete", return_value=True)
class DeletingAProductCleansTheCdn(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="Linen", sku="LIN1")
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="LIN1.WHITE")

    def _file(self, name, **kw):
        kw.setdefault("product", self.product)
        return ProductFile.objects.create(file_url=CDN + name, **kw)

    def _delete_product(self):
        with self.captureOnCommitCallbacks(execute=True):
            Product.objects.filter(pk=self.product.pk).delete()

    def _deleted(self, smart_delete):
        return sorted(c.args[0] for c in smart_delete.call_args_list)

    def test_its_files_variant_files_and_video_thumbnails_go(self, smart_delete):
        self._file("a.avif")
        self._file("clip.mp4", file_type="video", video_thumbnail=CDN + "clip.jpg")
        self._file("v.avif", product=None, product_variant=self.variant)
        self._delete_product()
        self.assertEqual(self._deleted(smart_delete),
                         [CDN + "a.avif", CDN + "clip.jpg", CDN + "clip.mp4", CDN + "v.avif"])

    def test_its_colour_swatches_go(self, smart_delete):
        attr = ProductVariantAttribute.objects.create(name="color")
        value = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attr, product_variant_attribute_value="white")
        VariantAttributeValueImage.objects.create(
            product=self.product, attribute_value=value, image_url=CDN + "swatch.jpg")
        self._delete_product()
        self.assertEqual(self._deleted(smart_delete), [CDN + "swatch.jpg"])

    def test_a_file_another_product_still_shows_stays(self, smart_delete):
        self._file("shared.avif")
        other = Product.objects.create(title="Silk", sku="SLK1")
        self._file("shared.avif", product=other)
        self._delete_product()
        smart_delete.assert_not_called()

    def test_a_file_a_group_uses_as_its_image_stays(self, smart_delete):
        self._file("hero.avif")
        ProductCategory.objects.create(name="fabric", image_url=CDN + "hero.avif")
        self._delete_product()
        smart_delete.assert_not_called()

    def test_two_rows_sharing_a_url_that_go_together_take_it_with_them(self, smart_delete):
        """Each row asks after the commit, when neither is left to hold the
        file. Both may send the delete; the second gets a 404, which Bunny
        treats as done."""
        self._file("dup.avif")
        self._file("dup.avif", product=None, product_variant=self.variant)
        self._delete_product()
        self.assertEqual(set(self._deleted(smart_delete)), {CDN + "dup.avif"})

    def test_a_delete_that_rolls_back_leaves_the_cdn_alone(self, smart_delete):
        self._file("a.avif")
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Product.objects.filter(pk=self.product.pk).delete()
                    raise RuntimeError
            except RuntimeError:
                pass
        smart_delete.assert_not_called()
        self.assertTrue(ProductFile.objects.filter(file_url=CDN + "a.avif").exists())

    def test_deleting_one_file_takes_it_off_the_cdn(self, smart_delete):
        f = self._file("a.avif")
        with self.captureOnCommitCallbacks(execute=True):
            f.delete()
        self.assertEqual(self._deleted(smart_delete), [CDN + "a.avif"])

    def test_skip_cdn_keeps_the_file(self, smart_delete):
        f = self._file("a.avif")
        with self.captureOnCommitCallbacks(execute=True):
            f.delete(skip_cdn=True)
        smart_delete.assert_not_called()
