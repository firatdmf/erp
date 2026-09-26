"""A cargo receipt photo is stored as a JPEG sized for its print.

JPEG because the receipt is mailed to the customer and every mail client
opens one; 2400 px because the small print must stay legible. HEIC from an
iPhone is converted, a sideways photo is stood up, and a PDF or anything
Pillow can't read is left exactly as it came.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from operating.receipt_images import MAX_LONG_EDGE_PX, optimize_receipt_image


def _image_file(name, fmt, size=(3000, 4000), content_type="image/png", exif=None, mode="RGB"):
    buf = io.BytesIO()
    img = Image.new(mode, size, "white")
    kwargs = {"exif": exif} if exif is not None else {}
    img.save(buf, format=fmt, **kwargs)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


def _open(jpeg):
    jpeg.seek(0)
    return Image.open(jpeg)


class ReceiptPhotosBecomeJpegs(SimpleTestCase):
    def test_a_large_photo_is_scaled_to_the_long_edge(self):
        jpeg = optimize_receipt_image(_image_file("slip.png", "PNG"))
        self.assertEqual((jpeg.name, jpeg.content_type), ("slip.jpg", "image/jpeg"))
        img = _open(jpeg)
        self.assertEqual(img.format, "JPEG")
        self.assertEqual(max(img.size), MAX_LONG_EDGE_PX)
        self.assertEqual(img.size, (1800, 2400))

    def test_an_iphone_heic_is_converted(self):
        import pillow_heif
        pillow_heif.register_heif_opener()
        heic = _image_file("IMG_0412.HEIC", "HEIF", size=(1200, 900), content_type="image/heic")
        jpeg = optimize_receipt_image(heic)
        self.assertEqual(jpeg.name, "IMG_0412.jpg")
        self.assertEqual(_open(jpeg).size, (1200, 900))

    def test_a_sideways_photo_is_stood_up(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # orientation: rotate 90° clockwise to view
        photo = _image_file("side.jpg", "JPEG", size=(4000, 3000),
                            content_type="image/jpeg", exif=exif.tobytes())
        self.assertEqual(_open(optimize_receipt_image(photo)).size, (1800, 2400))

    def test_a_transparent_png_goes_onto_white(self):
        png = _image_file("scan.png", "PNG", size=(400, 300), mode="RGBA")
        self.assertEqual(_open(optimize_receipt_image(png)).getpixel((5, 5)), (255, 255, 255))

    def test_a_small_clean_jpeg_is_left_alone(self):
        # Already a JPEG, and re-encoding comes out no smaller: keep it.
        small = _image_file("tiny.jpg", "JPEG", size=(200, 100), content_type="image/jpeg")
        small.size = 1
        self.assertIsNone(optimize_receipt_image(small))

    def test_a_pdf_or_unreadable_file_is_left_alone(self):
        pdf = SimpleUploadedFile("slip.pdf", b"%PDF-1.4 receipt", content_type="application/pdf")
        self.assertIsNone(optimize_receipt_image(pdf))
        self.assertEqual(pdf.read(), b"%PDF-1.4 receipt")  # rewound for the upload
