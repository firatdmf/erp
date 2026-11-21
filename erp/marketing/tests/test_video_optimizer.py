"""Product videos re-encoded light for the storefront.

Run with:
    python manage.py test marketing.tests.test_video_optimizer
"""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from marketing import video_optimizer
from marketing.models import Product, ProductFile, RetiredCdnFile

CDN = "https://cdn.example"
FOLDER = "media/product_images/K12767"


def url(path):
    return f"{CDN}/{path}"


def download(body=b"x" * 1000):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [body]
    return response


def writes(size):
    """A stand-in for encode/first_frame that writes `size` bytes."""
    def run(source, target):
        with open(target, "wb") as f:
            f.write(b"v" * size)
        return True
    return run


@override_settings(BUNNY_CDN_URL=CDN)
@patch("marketing.utils.bunny_storage.delete_from_bunny", return_value=True)
@patch("marketing.utils.bunny_storage.upload_to_bunny", side_effect=lambda f, path, **kw: url(path))
@patch("marketing.utils.bunny_storage.download_from_bunny", side_effect=lambda *a, **kw: download())
class Optimizing(TestCase):
    def setUp(self):
        cache.clear()
        self.product = Product.objects.create(title="Florenza", sku="K12767")
        self.old = url(f"{FOLDER}/florenza-aaaaaa.mp4")
        self.old_thumb = url(f"{FOLDER}/florenza-aaaaaa_thumb.jpg")
        # One video, shown by two rows (product + variant copy).
        self.rows = [
            ProductFile.objects.create(product=self.product, file_url=self.old, file_type="video",
                                       video_thumbnail=self.old_thumb)
            for _ in range(2)
        ]

    def _fresh(self):
        return [ProductFile.objects.get(pk=r.pk) for r in self.rows]

    @patch("marketing.video_optimizer.first_frame", side_effect=writes(10))
    @patch("marketing.video_optimizer.encode", side_effect=writes(400))
    def test_a_lighter_encode_replaces_the_file_for_every_row(self, encode, frame, dl, upload, delete):
        new_url = video_optimizer.optimize(self.old)
        self.assertRegex(new_url, rf"^{CDN}/{FOLDER}/florenza-[0-9a-f]{{6}}\.mp4$")
        for row in self._fresh():
            self.assertEqual(row.file_url, new_url)
            self.assertIsNotNone(row.video_optimized_at)
            self.assertRegex(row.video_thumbnail, r"-thumb\.jpg$")
            self.assertNotEqual(row.video_thumbnail, self.old_thumb)
        self.assertEqual(set(RetiredCdnFile.objects.values_list("url", flat=True)),
                         {self.old, self.old_thumb})
        self.assertTrue(all(c.kwargs["purge"] is False for c in upload.call_args_list))
        delete.assert_not_called()

    @patch("marketing.video_optimizer.first_frame", side_effect=writes(10))
    @patch("marketing.video_optimizer.encode", side_effect=writes(5000))
    def test_an_encode_that_comes_out_bigger_keeps_the_original(self, encode, frame, dl, upload, delete):
        self.assertEqual(video_optimizer.optimize(self.old), self.old)
        for row in self._fresh():
            self.assertEqual(row.file_url, self.old)
            self.assertIsNotNone(row.video_optimized_at)
        self.assertEqual(list(RetiredCdnFile.objects.values_list("url", flat=True)), [self.old_thumb])
        self.assertEqual(upload.call_count, 1)  # the still frame only

    @patch("marketing.video_optimizer.first_frame", return_value=False)
    @patch("marketing.video_optimizer.encode", return_value=False)
    def test_a_file_ffmpeg_cannot_read_is_left_as_it_is_and_not_tried_again(
            self, encode, frame, dl, upload, delete):
        video_optimizer.optimize(self.old)
        for row in self._fresh():
            self.assertEqual((row.file_url, row.video_thumbnail), (self.old, self.old_thumb))
            self.assertIsNotNone(row.video_optimized_at)
        self.assertEqual(video_optimizer.pending(), [])
        upload.assert_not_called()

    @patch("marketing.video_optimizer.encode", side_effect=video_optimizer.FfmpegMissing("ffmpeg"))
    def test_without_ffmpeg_the_videos_wait(self, encode, dl, upload, delete):
        self.assertEqual(video_optimizer.optimize_pending(), 0)
        self.assertEqual(video_optimizer.pending(), [self.old])

    @patch("marketing.video_optimizer.first_frame", side_effect=writes(10))
    def test_a_video_moved_meanwhile_leaves_no_stray_files(self, frame, dl, upload, delete):
        moved = url("media/product_images/K12767/K12767.G1/florenza-aaaaaa.mp4")

        def encode_while_it_moves(source, target):
            ProductFile.objects.filter(file_url=self.old).update(file_url=moved)
            return writes(400)(source, target)

        with patch("marketing.video_optimizer.encode", side_effect=encode_while_it_moves):
            self.assertIsNone(video_optimizer.optimize(self.old))
        self.assertEqual(delete.call_count, 2)  # the encoded file and its still frame
        self.assertEqual(video_optimizer.pending(), [moved])  # the next run takes it
        self.assertFalse(RetiredCdnFile.objects.exists())

    @patch("marketing.video_optimizer.encode")
    def test_a_copy_of_a_done_video_takes_its_still_frame_without_a_new_encode(
            self, encode, dl, upload, delete):
        ProductFile.objects.filter(pk=self.rows[0].pk).update(
            video_optimized_at="2026-11-21T00:00Z", video_thumbnail=url(f"{FOLDER}/done.jpg"))
        self.assertEqual(video_optimizer.optimize(self.old), self.old)
        copy = self._fresh()[1]
        self.assertEqual(copy.video_thumbnail, url(f"{FOLDER}/done.jpg"))
        self.assertIsNotNone(copy.video_optimized_at)
        encode.assert_not_called()
        dl.assert_not_called()
        upload.assert_not_called()

    @patch("marketing.video_optimizer.encode")
    def test_a_video_another_run_is_on_is_left_to_it(self, encode, dl, upload, delete):
        cache.add(f"marketing.video_optimizer:{self.old}", True, 60)
        self.assertIsNone(video_optimizer.optimize(self.old))
        encode.assert_not_called()

    def test_only_videos_on_our_cdn_still_to_do_are_pending(self, dl, upload, delete):
        ProductFile.objects.create(product=self.product, file_url=url(f"{FOLDER}/a.avif"))
        ProductFile.objects.create(product=self.product, file_url="https://elsewhere.example/v.mp4",
                                   file_type="video")
        done = ProductFile.objects.create(product=self.product, file_url=url(f"{FOLDER}/done.mp4"),
                                          file_type="video")
        ProductFile.objects.filter(pk=done.pk).update(video_optimized_at="2026-11-21T00:00Z")
        other = Product.objects.create(title="Silk", sku="SLK")
        ProductFile.objects.create(product=other, file_url=url("media/product_images/SLK/s.mp4"),
                                   file_type="video")
        self.assertEqual(video_optimizer.pending(self.product.pk), [self.old])
        self.assertEqual(len(video_optimizer.pending()), 2)


@override_settings(BUNNY_CDN_URL=CDN)
@patch("marketing.views.upload_to_bunny", side_effect=lambda file, path, **kw: url(path))
class UploadingAVideo(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(user)
        self.product = Product.objects.create(title="Florenza", sku="K12767")

    def test_the_upload_answers_at_once_and_the_video_is_made_light_after(self, upload):
        with patch("marketing.video_optimizer.optimize_after_commit") as later:
            answer = self.client.post("/marketing/api/instant_upload_file/", {
                "file": SimpleUploadedFile("clip.mp4", b"mp4", content_type="video/mp4"),
                "product_id": self.product.pk,
            }).json()
        self.assertTrue(answer["success"], answer)
        row = ProductFile.objects.get(pk=answer["file"]["id"])
        self.assertEqual(row.file_type, "video")
        self.assertIsNone(row.video_optimized_at)
        later.assert_called_once_with(self.product.pk)
        self.assertEqual(upload.call_count, 1)  # the video as it came; nothing else yet

    def test_a_photo_sets_off_nothing(self, upload):
        with patch("marketing.views.optimize_image", return_value=None), \
                patch("marketing.video_optimizer.optimize_after_commit") as later:
            self.client.post("/marketing/api/instant_upload_file/", {
                "file": SimpleUploadedFile("a.jpeg", b"jpeg", content_type="image/jpeg"),
                "product_id": self.product.pk,
            })
        later.assert_not_called()
