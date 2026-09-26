"""Make a cargo receipt photo small and readable everywhere.

A receipt is shot on a phone: 3–5 MB, often HEIC on an iPhone, often
lying on its side in EXIF. It is then shown on the order page and mailed
to the customer, so it is stored as a JPEG — the one format every browser
and mail client opens — scaled and compressed only as far as the print on
it stays legible.

Not marketing.utils.image_optimizer: that one makes product photos, as
AVIF at 1500 px and quality down to 40. AVIF won't open in half the
mail clients a receipt is sent to, and that much squeezing blurs a
barcode and a tracking number.
"""
import io
import logging
import os

logger = logging.getLogger(__name__)

# Enough for the small print on a receipt shot at arm's length.
MAX_LONG_EDGE_PX = 2400
JPEG_QUALITY = 82


class ReceiptJpeg(io.BytesIO):
    """The converted image, standing in for the uploaded file."""

    content_type = "image/jpeg"

    def __init__(self, data, name):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def optimize_receipt_image(uploaded):
    """`uploaded` as a JPEG ReceiptJpeg, or None to keep it as it came.

    None when it is not an image Pillow can read (a PDF, a damaged file),
    or when the JPEG would come out no smaller than an original that was
    already a JPEG — re-encoding a small, clean scan only loses detail.
    """
    try:
        from PIL import Image, ImageOps

        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            logger.warning("[receipt_images] pillow-heif missing; HEIC receipts stay as uploaded")

        uploaded.seek(0)
        img = Image.open(uploaded)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            # A transparent PNG goes onto white, as it would print.
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, "white")
                bg.paste(img, mask=img.getchannel("A"))
                img = bg
            else:
                img = img.convert("RGB")
        if max(img.size) > MAX_LONG_EDGE_PX:
            img.thumbnail((MAX_LONG_EDGE_PX, MAX_LONG_EDGE_PX), Image.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        data = out.getvalue()
    except Exception as exc:
        logger.info("[receipt_images] %s left as uploaded: %s", getattr(uploaded, "name", "?"), exc)
        return None
    finally:
        try:
            uploaded.seek(0)
        except Exception:
            pass

    was_jpeg = (getattr(uploaded, "content_type", "") or "").lower() == "image/jpeg"
    if was_jpeg and len(data) >= (getattr(uploaded, "size", 0) or 0):
        return None
    stem = os.path.splitext(os.path.basename(getattr(uploaded, "name", "") or "receipt"))[0]
    return ReceiptJpeg(data, f"{stem}.jpg")
