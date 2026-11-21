"""A heavy uploaded PDF has the photos inside it made for a profile.

A scanned invoice is one big photo per page. The photos are scaled to the
profile's long edge and saved as a JPEG at its quality; the text and the
page layout stay as they are. A PDF already light enough, one nothing gets
smaller in, or one that can't be opened, is handed back to be kept as it came.
"""
import io

import pikepdf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from erp.image_optimizer import DOCUMENT
from erp.pdf_optimizer import OptimizedPdf, optimize_pdf

TEXT = b"BT /F1 12 Tf 72 720 Td (Invoice PUR-2026-000200) Tj ET\n"


def _scan(size=(3000, 4000), pages=2, smask=False, name="hakan-invoice.pdf"):
    """A PDF whose pages each carry a heavy photo and a line of text."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    for _ in range(pages):
        buf = io.BytesIO()
        Image.effect_noise(size, 64).convert("RGB").save(buf, format="JPEG", quality=98)
        image = pikepdf.Stream(pdf, buf.getvalue())
        image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        image.Width, image.Height = size
        image.ColorSpace, image.BitsPerComponent = pikepdf.Name.DeviceRGB, 8
        image.Filter = pikepdf.Name.DCTDecode
        if smask:
            mask = pikepdf.Stream(pdf, b"\xff" * (size[0] * size[1]))
            mask.Type, mask.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            mask.Width, mask.Height = size
            mask.ColorSpace, mask.BitsPerComponent = pikepdf.Name.DeviceGray, 8
            image.SMask = mask
        page = pdf.add_blank_page(page_size=(595, 842))
        page.Resources = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(Im0=image), Font=pikepdf.Dictionary(F1=font))
        page.Contents = pdf.make_stream(b"q 595 0 0 842 0 0 cm /Im0 Do Q\n" + TEXT)
    out = io.BytesIO()
    pdf.save(out)
    return SimpleUploadedFile(name, out.getvalue(), content_type="application/pdf")


def _images(data):
    with pikepdf.open(io.BytesIO(data)) as pdf:
        return [(int(im.Width), int(im.Height))
                for page in pdf.pages for im in page.images.values()]


class OptimizePdfTest(SimpleTestCase):
    def test_a_scan_is_stored_lighter_with_its_photos_at_the_document_size(self):
        scan = _scan()
        out = optimize_pdf(scan, DOCUMENT)
        self.assertIsInstance(out, OptimizedPdf)
        self.assertEqual(out.name, "hakan-invoice.pdf")
        self.assertEqual(out.content_type, "application/pdf")
        self.assertLess(out.size, scan.size // 2)
        self.assertEqual(_images(out.getvalue()), [(1800, 2400), (1800, 2400)])

    def test_the_text_on_the_page_is_left_as_it_is(self):
        out = optimize_pdf(_scan(pages=1), DOCUMENT)
        with pikepdf.open(io.BytesIO(out.getvalue())) as pdf:
            self.assertIn(TEXT, pdf.pages[0].Contents.read_bytes())

    def test_a_light_pdf_is_kept_as_it_came(self):
        small = SimpleUploadedFile("note.pdf", b"%PDF-1.4 tiny", "application/pdf")
        self.assertIs(optimize_pdf(small, DOCUMENT), small)

    def test_an_image_with_a_transparency_mask_is_left_alone(self):
        scan = _scan(size=(1200, 1600), pages=1, smask=True)
        out = optimize_pdf(scan, DOCUMENT)
        data = out.getvalue() if isinstance(out, OptimizedPdf) else scan.read()
        self.assertEqual(_images(data), [(1200, 1600)])
        with pikepdf.open(io.BytesIO(data)) as pdf:
            image = next(iter(pdf.pages[0].images.values()))
            self.assertEqual(image.Filter, pikepdf.Name.DCTDecode)
            self.assertIn("/SMask", image)

    def test_a_damaged_pdf_is_handed_back_for_keeping(self):
        broken = SimpleUploadedFile("broken.pdf", b"%PDF-1.4 " + b"x" * 800_000,
                                    "application/pdf")
        self.assertIsNone(optimize_pdf(broken, DOCUMENT))
        self.assertEqual(broken.tell(), 0)
