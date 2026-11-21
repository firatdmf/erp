"""Make a PDF as light as what it is for allows: the image optimizer's
counterpart for PDFs.

What makes an uploaded PDF heavy is almost always the pictures in it: a
scanned invoice is one big photo per page. So the photos inside are
treated as optimize_image would treat them on their own, scaled to the
profile's long edge and saved as a JPEG at its quality. The text, the
vector drawing and the page layout are left as they are, so typed text
stays sharp and selectable. The streams are then recompressed and the file
rewritten with object streams.

    from erp.image_optimizer import DOCUMENT
    from erp.pdf_optimizer import OptimizedPdf, optimize_pdf
    smaller = optimize_pdf(upload, DOCUMENT)

The answer is one of three things, as with optimize_image:

  an OptimizedPdf  store this instead: the same pages, lighter, under
                   the same name.
  the input itself already no heavier than the profile's target_kb, or
                   nothing came out smaller; rewound, handed back as it came.
  None             not a PDF pikepdf opens (damaged, password-locked),
                   or pikepdf is missing. The input is rewound; keep it.

An image is left alone when changing it could change how the page looks:
one with a transparency mask or a Decode array, a 1-bit scan (stored as a
fax-style bitmap, which a JPEG would only make heavier), or one in a colour
space other than grey or RGB.
"""
import io
import logging
import os

logger = logging.getLogger(__name__)


class OptimizedPdf(io.BytesIO):
    """The rewritten PDF, standing in for the uploaded file."""

    content_type = "application/pdf"

    def __init__(self, data, name):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def _size_of(file):
    size = getattr(file, "size", None)
    if size is None:
        pos = file.tell()
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(pos)
    return size or 0


def _shrink_image(obj, profile):
    """Re-encode one image XObject in place if that makes it smaller.
    Returns True when it was replaced."""
    import pikepdf
    from PIL import Image

    if (obj.get("/ImageMask", False) or "/SMask" in obj or "/Mask" in obj
            or "/Decode" in obj or int(obj.get("/BitsPerComponent", 8)) != 8):
        return False
    img = pikepdf.PdfImage(obj).as_pil_image()
    if img.mode not in ("RGB", "L"):
        return False
    if max(img.size) > profile.max_edge:
        img.thumbnail((profile.max_edge, profile.max_edge), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=profile.quality, optimize=True)
    data = out.getvalue()
    # Re-encoding something that comes out no smaller only loses detail.
    if len(data) >= len(obj.read_raw_bytes()):
        return False
    obj.write(data, filter=pikepdf.Name.DCTDecode)
    if "/DecodeParms" in obj:
        del obj["/DecodeParms"]
    obj.Width, obj.Height = img.size
    obj.ColorSpace = pikepdf.Name.DeviceRGB if img.mode == "RGB" else pikepdf.Name.DeviceGray
    obj.BitsPerComponent = 8
    return True


def optimize_pdf(file, profile):
    """`file` (an upload, a file object or bytes) made lighter for
    `profile`. See the module docstring for the three possible answers."""
    source = io.BytesIO(file) if isinstance(file, (bytes, bytearray)) else file
    original_size = _size_of(source)
    if profile.target_kb and original_size <= profile.target_kb * 1024:
        return file
    try:
        import pikepdf

        source.seek(0)
        with pikepdf.open(io.BytesIO(source.read())) as pdf:
            if pdf.is_encrypted:
                return None
            shrunk = 0
            for obj in pdf.objects:
                if not isinstance(obj, pikepdf.Stream) or obj.get("/Subtype") != "/Image":
                    continue
                try:
                    shrunk += _shrink_image(obj, profile)
                except Exception as exc:  # one odd image keeps the rest going
                    logger.info("[pdf_optimizer] image left as it came: %s", exc)
            out = io.BytesIO()
            pdf.save(out, compress_streams=True, recompress_flate=True,
                     object_stream_mode=pikepdf.ObjectStreamMode.generate)
            data = out.getvalue()
    except Exception as exc:
        logger.info("[pdf_optimizer] %s left as it came (%s): %s",
                    getattr(file, "name", "document"), profile.name, exc)
        return None
    finally:
        try:
            source.seek(0)
        except Exception:
            pass

    if len(data) >= original_size:
        return file
    name = os.path.basename(getattr(file, "name", "") or "document.pdf")
    logger.info("[pdf_optimizer] %s (%s, %d images, %d KB → %d KB)",
                name, profile.name, shrunk, original_size // 1024, len(data) // 1024)
    return OptimizedPdf(data, name)
