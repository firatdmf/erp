"""Make an image as small as what it is for allows — one door for all of them.

Every place that stores or embeds a photo runs the same steps: open it
(HEIC from an iPhone included), stand it up from its EXIF orientation,
deal with transparency, scale it to a long edge, encode it. What differs
is only what the image is for, so a caller names that — a Profile — and
never passes numbers of its own:

  WEB       product, blog and review photos: AVIF, light enough for a
            storefront page.
  DOCUMENT  cargo receipts and files hung off CRM records: JPEG, which
            every browser and mail client opens, sized so small print
            stays legible.
  PRINT     photos embedded in the catalog PDF: print resolution for the
            largest frame in the layout.

A new place that takes images picks one of these, or adds a profile
here — not a copy of the steps.

    from erp.image_optimizer import DOCUMENT, optimize_image
    stored = optimize_image(upload, DOCUMENT) or upload

The answer is one of three things:

  an OptimizedImage  store this instead: smaller, upright, in the
                     profile's format, named <stem>.<ext>.
  the input itself   it already is that, as light as the profile asks;
                     it is rewound and handed back untouched.
  None               nothing this profile can make of it — not an image
                     Pillow reads (a PDF, a damaged file), an animated
                     one a still format would cut to its first frame,
                     or the encoder is missing. The input is rewound;
                     keep it as it came, or refuse it.
"""
import io
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Profile:
    name: str
    format: str            # Pillow format: "AVIF" or "JPEG"
    max_edge: int          # longest side, in pixels
    quality: int           # first encode
    # An original already in `format`, within `max_edge`, upright and no
    # heavier than this is kept as it came. An encode heavier than this
    # steps the quality down by 10 until it fits or reaches `min_quality`.
    target_kb: int | None = None
    min_quality: int | None = None
    # What happens to an image with an alpha channel:
    #   "keep"   encoded with it (AVIF holds alpha)
    #   "white"  laid onto white, as it would print
    #   "png"    saved as a PNG instead, so the cut-out survives
    transparency: str = "white"


WEB = Profile("web", "AVIF", max_edge=1500, quality=80,
              target_kb=300, min_quality=40, transparency="keep")
DOCUMENT = Profile("document", "JPEG", max_edge=2400, quality=82,
                   target_kb=700)
# The largest frame in the catalog is 62 mm wide: ~730 px at 300 dpi, so
# 1200 leaves headroom for bigger frames without bloating the PDF.
PRINT = Profile("print", "JPEG", max_edge=1200, quality=85,
                transparency="png")

EXTENSIONS = {"AVIF": ".avif", "JPEG": ".jpg", "PNG": ".png"}
CONTENT_TYPES = {"AVIF": "image/avif", "JPEG": "image/jpeg", "PNG": "image/png"}


class OptimizedImage(io.BytesIO):
    """The encoded image, standing in for the uploaded file."""

    def __init__(self, data, name, fmt):
        super().__init__(data)
        self.name = name
        self.content_type = CONTENT_TYPES[fmt]
        self.size = len(data)


_codecs_registered = False


def _register_codecs():
    """HEIC and AVIF in Pillow — each plugin registers itself on import."""
    global _codecs_registered
    if _codecs_registered:
        return
    _codecs_registered = True
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        logger.warning("[image_optimizer] pillow-heif missing; HEIC photos stay as uploaded")
    try:
        import pillow_avif  # noqa: F401 — not needed on Pillow >= 11.3
    except ImportError:
        pass


def _has_alpha(img):
    return (img.mode in ("RGBA", "LA", "PA")
            or (img.mode == "P" and "transparency" in img.info))


def _size_of(file):
    size = getattr(file, "size", None)
    if size is None:
        pos = file.tell()
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(pos)
    return size or 0


def optimize_image(file, profile):
    """`file` (an upload, a file object or bytes) made for `profile`.

    See the module docstring for the three possible answers.
    """
    source = io.BytesIO(file) if isinstance(file, (bytes, bytearray)) else file
    original_size = _size_of(source)
    try:
        from PIL import Image, ImageOps
        _register_codecs()

        source.seek(0)
        img = Image.open(source)
        if getattr(img, "is_animated", False):
            return None
        original_format = img.format
        alpha = _has_alpha(img)
        fmt = "PNG" if alpha and profile.transparency == "png" else profile.format

        if (profile.target_kb and original_format == fmt
                and img.mode in ("RGB", "RGBA")
                and max(img.size) <= profile.max_edge
                and original_size <= profile.target_kb * 1024
                and img.getexif().get(0x0112, 1) == 1):  # not lying on its side
            return file

        img = ImageOps.exif_transpose(img)
        if alpha and profile.transparency == "white":
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, "white")
            flat.paste(img, mask=img.getchannel("A"))
            img = flat
        elif alpha:
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        if max(img.size) > profile.max_edge:
            img.thumbnail((profile.max_edge, profile.max_edge), Image.LANCZOS)

        quality = profile.quality
        while True:
            out = io.BytesIO()
            if fmt == "PNG":
                img.save(out, format="PNG", optimize=True)
            elif fmt == "JPEG":
                img.save(out, format="JPEG", quality=quality,
                         optimize=True, progressive=True)
            else:
                img.save(out, format=fmt, quality=quality)
            data = out.getvalue()
            if (fmt == "PNG" or not profile.target_kb or not profile.min_quality
                    or len(data) <= profile.target_kb * 1024
                    or quality - 10 < profile.min_quality):
                break
            quality -= 10
    except Exception as exc:
        logger.info("[image_optimizer] %s left as it came (%s): %s",
                    getattr(file, "name", "image"), profile.name, exc)
        return None
    finally:
        try:
            source.seek(0)
        except Exception:
            pass

    # Re-encoding something already in this format that comes out no
    # smaller only loses detail.
    if original_format == fmt and len(data) >= original_size:
        return file

    stem = os.path.splitext(os.path.basename(getattr(file, "name", "") or "image"))[0]
    logger.info("[image_optimizer] %s → %s%s (%s, %d KB → %d KB, quality %s)",
                getattr(file, "name", "image"), stem, EXTENSIONS[fmt], profile.name,
                original_size // 1024, len(data) // 1024, quality)
    return OptimizedImage(data, f"{stem}{EXTENSIONS[fmt]}", fmt)
