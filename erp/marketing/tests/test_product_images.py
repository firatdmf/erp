"""Product photos: their CDN names, the folders that follow who uses them,
and the alt text built from the product as it is now.

Run with:
    python manage.py test marketing.tests.test_product_images
"""
import json
import re
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from marketing import product_images
from marketing.models import (
    CatalogWording, Product, ProductCategory, ProductFile, ProductVariant,
    ProductVariantAttribute, ProductVariantAttributeValue, RetiredCdnFile,
    VariantAttributeValueImage,
)

CDN = "https://cdn.example"
NAME = r"florenza-[0-9a-f]{6}"


def url(path):
    return f"{CDN}/{path}"


class NamesAndFolders(TestCase):
    def test_a_sku_keeps_its_case_and_dots(self):
        self.assertEqual(product_images.sku_segment("K12767.G141"), "K12767.G141")

    def test_what_a_path_cannot_carry_becomes_a_hyphen(self):
        self.assertEqual(product_images.sku_segment("AB 12/3"), "AB-12-3")
        self.assertEqual(product_images.sku_segment("Şile.Kırmızı"), "Sile.Kirmizi")

    def test_a_title_is_lowercased_and_spelled_in_plain_letters(self):
        self.assertEqual(product_images.title_slug("Florenza"), "florenza")
        self.assertEqual(product_images.title_slug("Kızılırmak Grek Pilise"), "kizilirmak-grek-pilise")
        self.assertEqual(product_images.title_slug("Флоренция"), "florentsiya")

    def test_a_name_is_the_title_and_a_random_suffix(self):
        product = Product(title="Florenza", sku="K12767")
        first = product_images.new_file_name(product, ".avif")
        self.assertRegex(first, rf"^{NAME}\.avif$")
        self.assertNotEqual(first, product_images.new_file_name(product, ".avif"))

    def test_a_product_with_no_title_still_gets_a_name(self):
        self.assertRegex(product_images.new_file_name(Product(title="", sku="X"), ".JPG"),
                         r"^image-[0-9a-f]{6}\.jpg$")

    def test_a_variants_folder_sits_in_its_products(self):
        product = Product.objects.create(title="Florenza", sku="K12767")
        variant = ProductVariant.objects.create(product=product, variant_sku="K12767.G141")
        self.assertEqual(product_images.folder_for(product), "media/product_images/K12767")
        self.assertEqual(product_images.folder_for(product, variant),
                         "media/product_images/K12767/K12767.G141")

    @override_settings(BUNNY_CDN_URL=CDN)
    def test_only_the_sku_folder_layout_is_ours_to_move(self):
        self.assertTrue(product_images.in_layout(url("media/product_images/K1/a.avif")))
        self.assertTrue(product_images.in_layout(url("media/product_images/K1/K1.G1/a.avif")))
        self.assertFalse(product_images.in_layout(url("media/product_images/product_K1/a.avif")))
        self.assertFalse(product_images.in_layout(
            url("media/product_images/product_K1/variant_K1.G1/a.avif")))
        self.assertFalse(product_images.in_layout(url("media/temp_product_files/u_1/a.avif")))
        self.assertFalse(product_images.in_layout("https://elsewhere.example/media/product_images/K1/a.avif"))


@override_settings(BUNNY_CDN_URL=CDN)
@patch("marketing.views.optimize_image", return_value=None)
@patch("marketing.views.upload_to_bunny", side_effect=lambda file, path, **kw: url(path))
class Uploading(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(user)
        self.product = Product.objects.create(title="Florenza", sku="K12767")
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="K12767.G141")

    def _upload(self, **extra):
        data = {"file": SimpleUploadedFile("K12767.G141-1.jpeg", b"jpeg", content_type="image/jpeg"),
                "product_id": self.product.pk, **extra}
        return self.client.post("/marketing/api/instant_upload_file/", data).json()

    def test_a_variant_editors_upload_lands_in_that_variants_folder_unlinked(self, upload, _):
        answer = self._upload(for_variant_id=self.variant.pk)
        self.assertTrue(answer["success"], answer)
        self.assertRegex(upload.call_args.args[1],
                         rf"^media/product_images/K12767/K12767\.G141/{NAME}\.jpeg$")
        row = ProductFile.objects.get(pk=answer["file"]["id"])
        self.assertIsNone(row.product_variant_id)  # joins the pool; the save links it

    def test_the_products_own_upload_lands_in_its_folder(self, upload, _):
        self._upload()
        self.assertRegex(upload.call_args.args[1], rf"^media/product_images/K12767/{NAME}\.jpeg$")

    def test_another_products_variant_is_no_folder_for_it(self, upload, _):
        other = Product.objects.create(title="Silk", sku="SLK")
        stranger = ProductVariant.objects.create(product=other, variant_sku="SLK.1")
        self._upload(for_variant_id=stranger.pk)
        self.assertRegex(upload.call_args.args[1], rf"^media/product_images/K12767/{NAME}\.jpeg$")

    def test_a_fresh_path_needs_no_cache_purge(self, upload, _):
        self._upload()
        self.assertIs(upload.call_args.kwargs["purge"], False)


@override_settings(BUNNY_CDN_URL=CDN)
@patch("marketing.utils.bunny_storage.upload_to_bunny", side_effect=lambda content, path, **kw: url(path))
@patch("marketing.utils.bunny_storage.download_from_bunny", return_value=MagicMock(content=b"img"))
class FoldersFollowUse(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="Florenza", sku="K12767")
        self.g141 = ProductVariant.objects.create(product=self.product, variant_sku="K12767.G141")
        self.g28 = ProductVariant.objects.create(product=self.product, variant_sku="K12767.G28")

    def _row(self, path, variant=None, **kw):
        return ProductFile.objects.create(product=self.product, product_variant=variant,
                                          file_url=url(path), **kw)

    def _urls(self):
        return sorted(ProductFile.objects.values_list("file_url", flat=True))

    def test_a_photo_one_variant_uses_moves_into_its_folder(self, download, upload):
        self._row("media/product_images/K12767/florenza-aaaaaa.avif", self.g141)
        self.assertEqual(product_images.relocate(self.product.pk), 1)
        self.assertEqual(self._urls(),
                         [url("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif")])

    def test_a_photo_several_variants_share_moves_up_to_the_product(self, download, upload):
        path = "media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif"
        self._row(path, self.g141)
        self._row(path, self.g28)
        product_images.relocate(self.product.pk)
        self.assertEqual(self._urls(), [url("media/product_images/K12767/florenza-aaaaaa.avif")] * 2)

    def test_and_back_down_when_one_variant_lets_it_go(self, download, upload):
        path = "media/product_images/K12767/florenza-aaaaaa.avif"
        self._row(path, self.g28)
        product_images.relocate(self.product.pk)
        self.assertEqual(self._urls(),
                         [url("media/product_images/K12767/K12767.G28/florenza-aaaaaa.avif")])

    def test_a_photo_nobody_picked_lives_with_the_product(self, download, upload):
        self._row("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif")
        product_images.relocate(self.product.pk)
        self.assertEqual(self._urls(), [url("media/product_images/K12767/florenza-aaaaaa.avif")])

    def test_a_photo_where_it_belongs_is_left_alone(self, download, upload):
        self._row("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif", self.g141)
        self.assertEqual(product_images.relocate(self.product.pk), 0)
        download.assert_not_called()
        upload.assert_not_called()

    def test_a_new_sku_takes_its_photos_along(self, download, upload):
        self._row("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif", self.g141)
        Product.objects.filter(pk=self.product.pk).update(sku="FLR1")
        ProductVariant.objects.filter(pk=self.g141.pk).update(variant_sku="FLR1.G141")
        product_images.relocate(self.product.pk)
        self.assertEqual(self._urls(), [url("media/product_images/FLR1/FLR1.G141/florenza-aaaaaa.avif")])

    def test_the_sweep_catches_a_sku_renamed_anywhere(self, download, upload):
        self._row("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif", self.g141)
        other = Product.objects.create(title="Silk", sku="SLK")
        ProductFile.objects.create(product=other,
                                   file_url=url("media/product_images/SLK/silk-cccccc.avif"))
        ProductVariant.objects.filter(pk=self.g141.pk).update(variant_sku="K12767.G141B")
        self.assertEqual(product_images.sweep(), 1)
        self.assertIn(url("media/product_images/K12767/K12767.G141B/florenza-aaaaaa.avif"), self._urls())

    def test_older_uploads_keep_their_urls(self, download, upload):
        self._row("media/product_images/product_K12767/variant_K12767.G141/IMG_1.jpg", self.g28)
        self.assertEqual(product_images.relocate(self.product.pk), 0)

    def test_a_photo_another_product_shows_too_stays(self, download, upload):
        path = "media/product_images/K12767/florenza-aaaaaa.avif"
        self._row(path, self.g141)
        other = Product.objects.create(title="Silk", sku="SLK")
        ProductFile.objects.create(product=other, file_url=url(path))
        self.assertEqual(product_images.relocate(self.product.pk), 0)

    def test_what_else_points_at_the_file_follows_it(self, download, upload):
        old = "media/product_images/K12767/florenza-aaaaaa.avif"
        self._row(old, self.g141)
        attr = ProductVariantAttribute.objects.create(name="color")
        value = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attr, product_variant_attribute_value="undyed")
        swatch = VariantAttributeValueImage.objects.create(
            product=self.product, attribute_value=value, image_url=url(old))
        product_images.relocate(self.product.pk)
        swatch.refresh_from_db()
        self.assertEqual(swatch.image_url,
                         url("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif"))

    def test_the_old_file_is_kept_for_a_week(self, download, upload):
        old = url("media/product_images/K12767/florenza-aaaaaa.avif")
        self._row("media/product_images/K12767/florenza-aaaaaa.avif", self.g141)
        product_images.relocate(self.product.pk)
        retired = RetiredCdnFile.objects.get()
        self.assertEqual(retired.url, old)
        self.assertAlmostEqual(retired.delete_after, timezone.now() + timedelta(days=7),
                               delta=timedelta(minutes=1))

    def test_a_video_takes_its_still_frame_along(self, download, upload):
        self._row("media/product_images/K12767/florenza-aaaaaa.mp4", self.g141, file_type="video",
                  video_thumbnail=url("media/product_images/K12767/florenza-aaaaaa.jpg"))
        product_images.relocate(self.product.pk)
        row = ProductFile.objects.get()
        self.assertEqual(row.video_thumbnail,
                         url("media/product_images/K12767/K12767.G141/florenza-aaaaaa.jpg"))

    def test_a_new_products_uploads_are_brought_in_under_its_name(self, download, upload):
        temp = url("media/temp_product_files/boss_1/K12767.G141-1.avif")
        self._row("media/temp_product_files/boss_1/K12767.G141-1.avif", self.g141)
        product_images.relocate(self.product.pk, adopt=[temp])
        self.assertRegex(self._urls()[0],
                         rf"^{re.escape(CDN)}/media/product_images/K12767/K12767\.G141/{NAME}\.avif$")

    def test_a_move_that_fails_leaves_the_photo_working_where_it_was(self, download, upload):
        download.side_effect = Exception("Bunny is down")
        self._row("media/product_images/K12767/florenza-aaaaaa.avif", self.g141)
        self.assertEqual(product_images.relocate(self.product.pk), 0)
        self.assertEqual(self._urls(), [url("media/product_images/K12767/florenza-aaaaaa.avif")])
        self.assertFalse(RetiredCdnFile.objects.exists())

    def test_the_move_runs_once_the_save_is_committed(self, download, upload):
        self._row("media/product_images/K12767/florenza-aaaaaa.avif", self.g141)
        with patch("marketing.product_images.threading.Thread") as thread, \
                patch("marketing.product_images.connection"):
            thread.side_effect = lambda target, daemon: MagicMock(start=target)
            with self.captureOnCommitCallbacks(execute=True):
                product_images.relocate_after_commit(self.product.pk)
        self.assertEqual(self._urls(),
                         [url("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif")])


@override_settings(BUNNY_CDN_URL=CDN)
@patch("marketing.utils.bunny_storage.delete_empty_bunny_folder", return_value=True)
@patch("marketing.utils.bunny_storage.delete_from_bunny", return_value=True)
class DeletingWhatAMoveLeftBehind(TestCase):
    OLD = url("media/product_images/K12767/K12767.G141/florenza-aaaaaa.avif")

    def _retire(self, days_ago):
        return RetiredCdnFile.objects.create(
            url=self.OLD, delete_after=timezone.now() - timedelta(days=days_ago))

    def test_a_file_whose_week_is_over_is_deleted_and_its_empty_folders_with_it(self, delete, folder):
        self._retire(1)
        self.assertEqual(product_images.delete_expired(), 1)
        delete.assert_called_once_with(self.OLD)
        self.assertEqual([c.args[0] for c in folder.call_args_list],
                         ["media/product_images/K12767/K12767.G141", "media/product_images/K12767"])
        self.assertFalse(RetiredCdnFile.objects.exists())

    def test_a_folder_still_holding_something_stops_the_climb(self, delete, folder):
        folder.return_value = False
        self._retire(1)
        product_images.delete_expired()
        self.assertEqual(folder.call_count, 1)

    def test_a_file_still_waiting_is_left(self, delete, folder):
        self._retire(-1)
        self.assertEqual(product_images.delete_expired(), 0)
        delete.assert_not_called()
        self.assertTrue(RetiredCdnFile.objects.exists())

    def test_a_file_used_again_is_kept(self, delete, folder):
        product = Product.objects.create(title="Florenza", sku="K12767")
        ProductFile.objects.create(product=product, file_url=self.OLD)
        self._retire(1)
        product_images.delete_expired()
        delete.assert_not_called()
        self.assertFalse(RetiredCdnFile.objects.exists())

    def test_a_delete_that_fails_is_tried_again_next_time(self, delete, folder):
        delete.return_value = False
        self._retire(1)
        product_images.delete_expired()
        self.assertTrue(RetiredCdnFile.objects.exists())
        folder.assert_not_called()


class AltText(TestCase):
    def setUp(self):
        cache.clear()
        for kind, scope, key, language, text in [
            ("group", "", "fabric", "tr", "Kumaş"),
            ("name", "", "color", "tr", "Renk"),
            ("value", "color", "undyed", "en", "Undyed"),
            ("value", "color", "undyed", "tr", "Boyasız"),
        ]:
            CatalogWording.objects.create(kind=kind, scope=scope, key=key, language=language, text=text)

    def _alt(self, attributes, description=""):
        return product_images.alt_texts("Florenza", description, "fabric", attributes)

    def test_a_variants_photo_says_what_the_variant_is_in_each_language(self):
        texts = self._alt([("yarn", "103_semi-matte_gold"), ("color", "undyed"), ("width", "320")])
        self.assertEqual(texts["en"], "Florenza, Fabric. Color: Undyed, Width: 320 cm, Yarn: 103 semi-matte gold")
        self.assertEqual(texts["tr"], "Florenza, Kumaş. Renk: Boyasız, Width: 320 cm, Yarn: 103 semi-matte gold")
        self.assertEqual(set(texts), {"en", "tr", "ru"})

    def test_a_value_that_says_nothing_is_left_out(self):
        self.assertEqual(self._alt([("embellishment", "none"), ("color", "undyed")])["en"],
                         "Florenza, Fabric. Color: Undyed")

    def test_the_products_own_photo_names_the_product(self):
        self.assertEqual(self._alt([])["en"], "Florenza, Fabric")

    def test_a_translated_title_is_used_in_its_language(self):
        description = json.dumps({"translations": {"ru": {"title": "Флоренция"}}})
        texts = self._alt([], description)
        self.assertEqual(texts["ru"], "Флоренция, Fabric")
        self.assertEqual(texts["en"], "Florenza, Fabric")


class SharedPhotoAltText(TestCase):
    """A photo several variants share says only what they have in common."""

    def setUp(self):
        cache.clear()
        self.pairs = {
            1: [("color", "undyed"), ("fabric", "greek_tulle"), ("yarn", "103_semi-matte_gold")],
            2: [("color", "white"), ("fabric", "greek_tulle"), ("yarn", "630_matte")],
        }

    def _alts(self, rows):
        texts = product_images.alt_texts_by_row(rows, "Florenza", "", "fabric", self.pairs)
        return {row_id: t["en"] for row_id, t in texts.items()}

    def test_a_shared_photo_reads_the_same_for_each_variant_and_names_what_they_share(self):
        rows = [{"id": 10, "file_url": "a", "product_variant_id": 1},
                {"id": 11, "file_url": "a", "product_variant_id": 2}]
        self.assertEqual(self._alts(rows), {10: "Florenza, Fabric. Fabric: Greek tulle",
                                            11: "Florenza, Fabric. Fabric: Greek tulle"})

    def test_a_photo_of_one_variant_reads_as_that_variant(self):
        rows = [{"id": 10, "file_url": "a", "product_variant_id": 1},
                {"id": 11, "file_url": "b", "product_variant_id": 2}]
        self.assertEqual(self._alts(rows)[11],
                         "Florenza, Fabric. Color: White, Fabric: Greek tulle, Yarn: 630 matte")

    def test_a_photo_in_the_pool_reads_as_the_product(self):
        self.assertEqual(self._alts([{"id": 10, "file_url": "a", "product_variant_id": None}]),
                         {10: "Florenza, Fabric"})


class AltTextInTheStorefrontApi(TestCase):
    def setUp(self):
        cache.clear()
        group = ProductCategory.objects.create(name="fabric")
        self.product = Product.objects.create(title="Florenza", sku="K12767", featured=True, category=group)
        color = ProductVariantAttribute.objects.create(name="color")
        fabric = ProductVariantAttribute.objects.create(name="fabric")
        tulle = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=fabric, product_variant_attribute_value="greek_tulle")
        self.g141 = ProductVariant.objects.create(product=self.product, variant_sku="K12767.G141")
        self.g141.product_variant_attribute_values.add(tulle, ProductVariantAttributeValue.objects.create(
            product_variant_attribute=color, product_variant_attribute_value="undyed"))
        self.g28 = ProductVariant.objects.create(product=self.product, variant_sku="K12767.G28")
        self.g28.product_variant_attribute_values.add(tulle, ProductVariantAttributeValue.objects.create(
            product_variant_attribute=color, product_variant_attribute_value="white"))
        # One photo of G141's own, and one both variants picked: a row each.
        ProductFile.objects.create(product=self.product, product_variant=self.g141,
                                   file_url=url("media/product_images/K12767/K12767.G141/florenza-bbbbbb.avif"))
        for variant in (self.g141, self.g28):
            ProductFile.objects.create(product=self.product, product_variant=variant,
                                       file_url=url("media/product_images/K12767/florenza-aaaaaa.avif"))

    def _alts(self, files):
        return sorted((f["file"].rsplit("/", 1)[-1], f["alt_texts"]["en"]) for f in files)

    EXPECTED = [
        ("florenza-aaaaaa.avif", "Florenza, Fabric. Fabric: Greek tulle"),
        ("florenza-aaaaaa.avif", "Florenza, Fabric. Fabric: Greek tulle"),
        ("florenza-bbbbbb.avif", "Florenza, Fabric. Color: Undyed, Fabric: Greek tulle"),
    ]

    def test_each_photo_says_what_it_shows(self):
        files = self.client.get("/marketing/api/get_product", {"product_sku": "K12767"}).json()["product_files"]
        self.assertEqual(self._alts(files), self.EXPECTED)

    def test_the_product_list_carries_it_too(self):
        products = self.client.get("/marketing/api/get_products").json()["products"]
        self.assertEqual(self._alts(products[0]["product_files"]), self.EXPECTED)

    def test_a_typed_alt_text_is_still_sent(self):
        ProductFile.objects.filter(product_variant=self.g28).update(alt_text="Every colourway")
        files = self.client.get("/marketing/api/get_product", {"product_sku": "K12767"}).json()["product_files"]
        typed = {f["product_variant_id"]: f["alt_text"] for f in files if f["alt_text"]}
        self.assertEqual(typed, {self.g28.pk: "Every colourway"})


@override_settings(BUNNY_CDN_URL=CDN)
class HourlyHousekeeping(TestCase):
    def setUp(self):
        cache.clear()

    def _run(self):
        with patch("marketing.product_images.threading.Thread") as thread, \
                patch("marketing.product_images.connection"), \
                patch("marketing.product_images.sweep") as sweep, \
                patch("marketing.product_images.delete_expired") as delete_expired:
            thread.side_effect = lambda target, daemon: MagicMock(start=target)
            with self.captureOnCommitCallbacks(execute=True):
                product_images.housekeep_now_and_then()
        return sweep.call_count, delete_expired.call_count

    def test_the_storefronts_calls_set_it_off_at_most_once_an_hour(self):
        self.assertEqual(self._run(), (1, 1))
        self.assertEqual(self._run(), (0, 0))

    def test_a_storefront_call_sets_it_off(self):
        with patch("marketing.product_images.housekeep_now_and_then") as housekeep:
            self.client.get("/marketing/api/get_products")
            self.client.get("/marketing/api/get_product", {"product_sku": "nothing"})
        self.assertEqual(housekeep.call_count, 2)
