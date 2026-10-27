"""Every stored or embedded photo goes through one optimizer, by profile.

DOCUMENT is a JPEG a mail client opens, 2400 px so small print stays
legible (cargo receipts, CRM files). WEB is a light AVIF for the
storefront (product, blog and review photos). PRINT is print resolution
for the catalog PDF, a PNG where a cut-out must survive. Whatever the
profile, HEIC from an iPhone is read, a sideways photo is stood up, and
what Pillow can't read — or an animation a still would cut short — is
handed back to be kept as it came.
"""
import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from erp.image_optimizer import DOCUMENT, PRINT, WEB, OptimizedImage, optimize_image


def _image_file(name, fmt, size=(3000, 4000), content_type="image/png", exif=None, mode="RGB"):
    buf = io.BytesIO()
    img = Image.new(mode, size, "white")
    kwargs = {"exif": exif} if exif is not None else {}
    img.save(buf, format=fmt, **kwargs)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


def _noise_jpeg(name, size):
    buf = io.BytesIO()
    Image.effect_noise(size, 64).convert("RGB").save(buf, format="JPEG", quality=98)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _sideways_exif():
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90° clockwise to view
    return exif.tobytes()


def _open(out):
    out.seek(0)
    return Image.open(out)


class DocumentPhotosBecomeJpegs(SimpleTestCase):
    def test_a_large_photo_is_scaled_to_the_long_edge(self):
        jpeg = optimize_image(_image_file("slip.png", "PNG"), DOCUMENT)
        self.assertIsInstance(jpeg, OptimizedImage)
        self.assertEqual((jpeg.name, jpeg.content_type), ("slip.jpg", "image/jpeg"))
        img = _open(jpeg)
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(img.size, (1800, 2400))

    def test_an_iphone_heic_is_converted(self):
        import pillow_heif
        pillow_heif.register_heif_opener()
        heic = _image_file("IMG_0412.HEIC", "HEIF", size=(1200, 900), content_type="image/heic")
        jpeg = optimize_image(heic, DOCUMENT)
        self.assertEqual(jpeg.name, "IMG_0412.jpg")
        self.assertEqual(_open(jpeg).size, (1200, 900))

    def test_a_sideways_photo_is_stood_up(self):
        photo = _image_file("side.jpg", "JPEG", size=(4000, 3000),
                            content_type="image/jpeg", exif=_sideways_exif())
        self.assertEqual(_open(optimize_image(photo, DOCUMENT)).size, (1800, 2400))

    def test_a_small_photo_on_its_side_is_still_stood_up(self):
        photo = _image_file("side.jpg", "JPEG", size=(1200, 900),
                            content_type="image/jpeg", exif=_sideways_exif())
        self.assertEqual(_open(optimize_image(photo, DOCUMENT)).size, (900, 1200))

    def test_a_transparent_png_goes_onto_white(self):
        png = _image_file("scan.png", "PNG", size=(400, 300), mode="RGBA")
        out = optimize_image(png, DOCUMENT)
        self.assertEqual(_open(out).getpixel((5, 5)), (255, 255, 255))

    def test_a_jpeg_that_would_come_out_no_smaller_is_handed_back(self):
        small = _image_file("tiny.jpg", "JPEG", size=(200, 100), content_type="image/jpeg")
        small.size = 1
        self.assertIs(optimize_image(small, DOCUMENT), small)

    def test_a_photo_already_shrunk_is_not_encoded_again(self):
        # What the order page sends: a JPEG within the long edge, upright, light.
        sent = _image_file("slip.jpg", "JPEG", size=(2400, 1800), content_type="image/jpeg")
        with patch("PIL.Image.Image.save") as encode:
            self.assertIs(optimize_image(sent, DOCUMENT), sent)
        encode.assert_not_called()
        self.assertEqual(sent.tell(), 0)  # rewound for the upload

    def test_a_pdf_or_unreadable_file_is_left_alone(self):
        pdf = SimpleUploadedFile("slip.pdf", b"%PDF-1.4 receipt", content_type="application/pdf")
        self.assertIsNone(optimize_image(pdf, DOCUMENT))
        self.assertEqual(pdf.read(), b"%PDF-1.4 receipt")  # rewound for the upload

    def test_an_animation_is_not_cut_to_its_first_frame(self):
        buf = io.BytesIO()
        frames = [Image.new("RGB", (50, 50), c) for c in ("red", "blue")]
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:])
        gif = SimpleUploadedFile("wave.gif", buf.getvalue(), content_type="image/gif")
        self.assertIsNone(optimize_image(gif, DOCUMENT))


class WebPhotosBecomeLightAvifs(SimpleTestCase):
    def test_a_phone_photo_becomes_an_avif_within_the_edge_and_target(self):
        avif = optimize_image(_noise_jpeg("sofa.jpg", (4000, 3000)), WEB)
        self.assertEqual((avif.name, avif.content_type), ("sofa.avif", "image/avif"))
        self.assertEqual(_open(avif).size, (1500, 1125))
        self.assertLessEqual(avif.size, WEB.target_kb * 1024)

    def test_transparency_is_kept(self):
        buf = io.BytesIO()
        Image.new("RGBA", (400, 300), (255, 255, 255, 0)).save(buf, format="PNG")
        png = SimpleUploadedFile("cutout.png", buf.getvalue(), content_type="image/png")
        self.assertEqual(_open(optimize_image(png, WEB)).getpixel((5, 5))[3], 0)


class PrintPhotosForTheCatalog(SimpleTestCase):
    def test_bytes_are_scaled_to_print_resolution(self):
        raw = _noise_jpeg("p.jpg", (4000, 3000)).read()
        out = optimize_image(raw, PRINT)
        self.assertEqual(out.content_type, "image/jpeg")
        self.assertEqual(_open(out).size, (1200, 900))

    def test_a_cut_out_stays_a_png(self):
        raw = _image_file("cutout.png", "PNG", size=(2000, 1000), mode="RGBA").read()
        out = optimize_image(raw, PRINT)
        self.assertEqual(out.content_type, "image/png")
        self.assertEqual(_open(out).mode, "RGBA")
