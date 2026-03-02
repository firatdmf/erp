"""
Image Optimizer Utility
=======================
Converts JPEG/PNG images to AVIF format before uploading to CDN.
Inspired by: https://github.com/firatdmf/python_image_optimizer

Dependencies (add to requirements.txt):
  pillow>=10.0.0         (should already be present)
  pillow-avif-plugin>=1.4.1

Usage:
  from marketing.utils.image_optimizer import optimize_image_to_avif
  optimized_file = optimize_image_to_avif(original_django_uploaded_file)
  # optimized_file is a BytesIO with .name and .content_type attributes
"""

import io
import math
import logging

logger = logging.getLogger(__name__)

# Target constraints
MAX_LONG_EDGE_PX = 1500       # Max dimension (longest side)
TARGET_MAX_SIZE_KB = 300      # Target maximum file size in KB
INITIAL_QUALITY = 80          # Start quality
MIN_QUALITY = 40              # Never go below this quality
QUALITY_STEP = 10             # Decrease quality by this step each iteration


class OptimizedImageFile:
    """
    Wrapper that mimics Django's InMemoryUploadedFile interface
    so it can be passed directly to smart_upload / Cloudinary / Bunny.
    """
    def __init__(self, buffer: io.BytesIO, original_name: str):
        self.buffer = buffer
        # Change extension to .avif
        stem = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        self.name = f"{stem}.avif"
        self.content_type = "image/avif"
        self._pos = 0

    # --- File-like interface ---
    def read(self, size=-1):
        self.buffer.seek(self._pos)
        data = self.buffer.read(size) if size >= 0 else self.buffer.read()
        self._pos = self.buffer.tell()
        return data

    def seek(self, offset, whence=0):
        self.buffer.seek(offset, whence)
        self._pos = self.buffer.tell()

    def tell(self):
        return self.buffer.tell()

    def __len__(self):
        pos = self.buffer.tell()
        self.buffer.seek(0, 2)  # seek to end
        size = self.buffer.tell()
        self.buffer.seek(pos)
        return size

    # Django's storage backends also check these:
    @property
    def size(self):
        return len(self)

    def chunks(self):
        self.buffer.seek(0)
        while True:
            chunk = self.buffer.read(65536)
            if not chunk:
                break
            yield chunk


def optimize_image_to_avif(django_file) -> "OptimizedImageFile | None":
    """
    Take a Django UploadedFile (JPEG, PNG, WEBP, etc.) and return a
    BytesIO-based wrapper containing the AVIF-converted, optimized version.

    Returns None if conversion fails (caller should fall back to original).
    """
    try:
        # Attempt to import pillow_avif plugin
        try:
            import pillow_avif  # noqa: F401  – registers AVIF plugin in Pillow
        except ImportError:
            logger.warning(
                "[image_optimizer] pillow-avif-plugin is not installed. "
                "Skipping AVIF conversion. Run: pip install pillow-avif-plugin"
            )
            return None

        from PIL import Image, ImageOps

        # Read original file
        django_file.seek(0)
        img = Image.open(django_file)

        # Ensure RGBA / palette images are properly converted for AVIF
        if img.mode in ('P', 'RGBA'):
            img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Fix EXIF orientation (prevents rotated thumbnails)
        img = ImageOps.exif_transpose(img)

        # ── Step 1: Resize if too large ──────────────────────────────────
        width, height = img.size
        long_edge = max(width, height)
        if long_edge > MAX_LONG_EDGE_PX:
            scale = MAX_LONG_EDGE_PX / long_edge
            new_w = int(width * scale)
            new_h = int(height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            logger.debug(f"[image_optimizer] Resized {width}x{height} → {new_w}x{new_h}")

        # ── Step 2: Convert to AVIF iterating quality until size target ──
        quality = INITIAL_QUALITY
        output = io.BytesIO()

        while quality >= MIN_QUALITY:
            output = io.BytesIO()
            save_kwargs = {
                "format": "AVIF",
                "quality": quality,
            }
            # AVIF supports alpha; use RGB mode when no alpha
            if img.mode == 'RGBA':
                img.save(output, **save_kwargs)
            else:
                img.convert('RGB').save(output, **save_kwargs)

            size_kb = math.ceil(output.tell() / 1024)
            logger.debug(f"[image_optimizer] AVIF quality={quality} → {size_kb} KB")

            if size_kb <= TARGET_MAX_SIZE_KB:
                break
            quality -= QUALITY_STEP

        output.seek(0)
        original_name = getattr(django_file, 'name', 'image.jpg')
        result = OptimizedImageFile(output, original_name)

        final_size_kb = math.ceil(len(result) / 1024)
        logger.info(
            f"[image_optimizer] '{original_name}' → '{result.name}' "
            f"({final_size_kb} KB, quality={quality})"
        )
        return result

    except Exception as exc:
        logger.warning(f"[image_optimizer] Optimization failed: {exc}. Falling back to original.")
        return None
