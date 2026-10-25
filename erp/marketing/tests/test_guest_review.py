"""A guest review arrives from the storefront's server with its photos; the
ERP stores them on Bunny, so the storefront needs no Bunny credentials.

See marketing.views.guest_review.
"""
import io
import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from marketing.models import GuestProductReview, Product


def jpeg(name="photo.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(STOREFRONT_API_KEY="shared-key")
class GuestReviewTests(TestCase):
    url = "/marketing/api/guest_review/"

    def setUp(self):
        Product.objects.create(title="Florenza", sku="K12767")
        self.fields = {"product_sku": "K12767", "first_name": "Ayşe", "last_name": "Kaya",
                       "hide_name": "true", "rating": "5", "comment": "Lovely"}
        upload = mock.patch("marketing.utils.bunny_storage.upload_to_bunny",
                            side_effect=lambda f, path, **kw: f"https://cdn.example/{path}")
        self.upload = upload.start()
        self.addCleanup(upload.stop)

    def test_photos_are_stored_on_bunny_as_avif(self):
        r = self.client.post(self.url, {**self.fields, "images": [jpeg(), jpeg("b.png")]},
                             HTTP_X_STOREFRONT_KEY="shared-key")
        self.assertEqual(r.json()["success"], True)
        review = GuestProductReview.objects.get()
        self.assertTrue(review.hide_name)
        self.assertEqual(sorted(i.image_url for i in review.images.all()), [
            f"https://cdn.example/reviews/K12767/{review.pk}-1.avif",
            f"https://cdn.example/reviews/K12767/{review.pk}-2.avif"])
        self.assertEqual(self.upload.call_args.kwargs["content_type"], "image/avif")

    def test_a_file_that_is_not_an_image_is_left_out(self):
        junk = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
        r = self.client.post(self.url, {**self.fields, "images": [junk]},
                             HTTP_X_STOREFRONT_KEY="shared-key")
        self.assertEqual(r.json()["success"], True)
        self.assertFalse(GuestProductReview.objects.get().images.exists())
        self.upload.assert_not_called()

    def test_photos_only_from_the_storefronts_server(self):
        r = self.client.post(self.url, {**self.fields, "images": [jpeg()]})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(GuestProductReview.objects.exists())
        self.upload.assert_not_called()

    def test_the_old_json_body_still_works(self):
        body = {**self.fields, "hide_name": False, "rating": 4,
                "image_urls": ["https://cdn.example/reviews/old.avif"]}
        r = self.client.post(self.url, json.dumps(body), content_type="application/json")
        self.assertEqual(r.json()["success"], True)
        review = GuestProductReview.objects.get()
        self.assertFalse(review.hide_name)
        self.assertEqual([i.image_url for i in review.images.all()], ["https://cdn.example/reviews/old.avif"])

    def test_deleting_a_review_deletes_its_photos_from_bunny(self):
        self.client.post(self.url, {**self.fields, "images": [jpeg()]}, HTTP_X_STOREFRONT_KEY="shared-key")
        review = GuestProductReview.objects.get()
        photo = f"https://cdn.example/reviews/K12767/{review.pk}-1.avif"
        with mock.patch("marketing.views.smart_delete") as delete, self.captureOnCommitCallbacks(execute=True):
            review.delete()
        delete.assert_called_once_with(photo)
