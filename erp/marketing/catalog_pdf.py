"""Product catalog → PDF (WeasyPrint).

The catalog is a DESIGNED document (alternating photo/text blocks, brand
wordmark, footer bar), so the layout is authored in HTML/CSS rather than in
reportlab drawing calls the way warehouse_label.py / order_notifications.py
are. Same reasoning as operating.views.OrderPrint: for design-heavy pages the
browser/CSS engine reproduces the design, hand-placed coordinates don't.

One template feeds two outputs — an HTML preview you can iterate on in the
browser, and the PDF — so what you preview is what you download.

Two macOS/deployment notes:
  - WeasyPrint needs pango/cairo/gdk-pixbuf as SYSTEM libs. On macOS they
    live in /opt/homebrew/lib, which is not on the dynamic loader path, so
    the import fails unless DYLD_FALLBACK_LIBRARY_PATH includes it. We set
    it here at import time (see _ensure_dyld_path) so `manage.py runserver`
    works without the developer exporting anything.
  - Its default urllib fetcher does not use certifi, so https images fail
    with CERTIFICATE_VERIFY_FAILED on macOS. url_fetcher below routes
    through `requests` instead, which also gives us timeouts and lets
    /static/ resolve off the filesystem rather than over self-HTTP.
"""
from __future__ import annotations

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

# Product photos are AVIF on the CDN. Pillow only decodes AVIF natively from
# 11.3 onwards — on an older Pillow every image silently renders as a blank
# box, so fail loudly at render time instead (see check_image_support).
_AVIF_HINT = (
    "Product images are AVIF; this Pillow cannot decode them. "
    "Upgrade Pillow (>=11.3) or install pillow-avif-plugin."
)


def _ensure_dyld_path():
    """macOS: put Homebrew's lib dir on the loader path before WeasyPrint's
    cffi dlopen() runs, otherwise `import weasyprint` raises OSError."""
    import sys
    if sys.platform != "darwin":
        return
    key = "DYLD_FALLBACK_LIBRARY_PATH"
    brew_lib = "/opt/homebrew/lib"
    if not os.path.isdir(brew_lib):
        return
    current = os.environ.get(key, "")
    if brew_lib not in current.split(":"):
        os.environ[key] = f"{current}:{brew_lib}".lstrip(":")


def check_image_support():
    """True if Pillow can decode the AVIF product photos.

    Two ways to get there: Pillow >= 11.3 decodes AVIF natively, older ones
    need pillow-avif-plugin, which registers the codec purely as an import
    side effect (same trick marketing/utils/image_optimizer.py uses).
    """
    try:
        import pillow_avif  # noqa: F401  – registers AVIF in Pillow
    except ImportError:
        pass
    try:
        from PIL import features
        return bool(features.check("avif"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# URL fetching
# ---------------------------------------------------------------------------
def _static_path(url: str):
    """Filesystem path for a /static/… URL, or None if it isn't one.

    Resolving statics off disk keeps PDF generation from making HTTP calls
    back to our own server — which would need the site to be reachable from
    itself and would break in a worker/cron context.

    We match on the URL's PATH, not the raw string: WeasyPrint resolves the
    stylesheet's "/static/…" against base_url first, so by the time it
    reaches us it is an absolute "file:///static/…" (or http://…/static/…).
    Matching the raw string missed those and the @font-face silently fell
    back to a serif.
    """
    from urllib.parse import urlparse

    static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
    path_part = urlparse(url).path or url
    if not path_part.startswith(static_url):
        return None
    relative = path_part[len(static_url):].split("?")[0]

    from django.contrib.staticfiles import finders
    found = finders.find(relative)
    if found:
        return found
    # Collected statics (production): fall back to STATIC_ROOT.
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        candidate = os.path.join(static_root, relative)
        if os.path.exists(candidate):
            return candidate
    return None


def url_fetcher(url: str):
    """WeasyPrint fetcher: statics off disk, remote images via requests."""
    if url.startswith("data:"):
        from weasyprint import default_url_fetcher
        return default_url_fetcher(url)

    path = _static_path(url)
    if path:
        return {"file_obj": open(path, "rb")}

    if url.startswith(("http://", "https://")):
        import requests
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";")[0] or None
        if (content_type or "").startswith("image/"):
            return _downscale(response.content, content_type)
        return {"string": response.content, "mime_type": content_type}

    from weasyprint import default_url_fetcher
    return default_url_fetcher(url)


# Longest edge we keep for an embedded photo. The largest frame in the layout
# is 62mm wide; at 300dpi that is ~730px, so 1200 leaves headroom for bigger
# frames without bloating the file.
MAX_IMAGE_EDGE = 1200


def _downscale(raw: bytes, content_type: str | None):
    """Shrink a source photo to print resolution before embedding.

    WeasyPrint embeds whatever pixels it is given. The CDN originals are
    full-resolution, which made a ONE-page catalog a 9.6MB PDF — a 7-page one
    would have been unmailable. Downscaling to print resolution is
    visually lossless at 62mm wide and cuts the file by ~50x.
    """
    from io import BytesIO
    try:
        from PIL import Image
        image = Image.open(BytesIO(raw))
        image.load()
        if max(image.size) > MAX_IMAGE_EDGE:
            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.LANCZOS)

        buffer = BytesIO()
        if image.mode in ("RGBA", "LA", "P"):
            image.convert("RGBA").save(buffer, format="PNG", optimize=True)
            return {"string": buffer.getvalue(), "mime_type": "image/png"}
        image.convert("RGB").save(buffer, format="JPEG", quality=85, optimize=True)
        return {"string": buffer.getvalue(), "mime_type": "image/jpeg"}
    except Exception:
        # A photo we cannot process is better embedded as-is than dropped.
        logger.exception("catalog image downscale failed; embedding original")
        return {"string": raw, "mime_type": content_type}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def read_catalog_css() -> str:
    """The print stylesheet, inlined into the template.

    Inlining (rather than <link>ing) guarantees the browser preview and the
    PDF use byte-identical CSS — no chance of one resolving the stylesheet
    and the other silently falling back to unstyled output.
    """
    path = _static_path(f"{settings.STATIC_URL}marketing/catalog/catalog_print.css")
    if not path:
        from django.contrib.staticfiles import finders
        path = finders.find("marketing/catalog/catalog_print.css")
    if not path:
        logger.error("catalog_print.css not found — catalog will render unstyled")
        return ""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _base_url() -> str:
    """A real file:// URL for resolving the document's relative references.

    Must be a URL, not a bare filesystem path: given a path with no scheme
    WeasyPrint silently ignores it, and every "/static/…" reference —
    including the @font-face — is dropped without so much as a warning. That
    is what made the first version render in fallback serif.
    """
    from pathlib import Path
    return Path(settings.BASE_DIR).as_uri() + "/"


def render_catalog_pdf(html: str, base_url: str | None = None) -> bytes:
    """Rendered catalog HTML → PDF bytes."""
    _ensure_dyld_path()
    from weasyprint import HTML

    if not check_image_support():
        logger.warning(_AVIF_HINT)

    return HTML(
        string=html,
        base_url=base_url or _base_url(),
        url_fetcher=url_fetcher,
    ).write_pdf()


_ensure_dyld_path()
# Registers the AVIF codec up front, so _downscale() can decode product photos
# even when the fetcher is driven outside render_catalog_pdf().
check_image_support()
