"""Product catalog → PDF (WeasyPrint).

The catalog is a DESIGNED document (alternating photo/text blocks, brand
wordmark, footer bar), so the layout is authored in HTML/CSS rather than in
reportlab drawing calls the way warehouse_label.py / order_notifications.py
are. Same reasoning as operating.views.OrderPrint: for design-heavy pages the
browser/CSS engine reproduces the design, hand-placed coordinates don't.

One template feeds two outputs — an HTML preview you can iterate on in the
browser, and the PDF — so what you preview is what you download.

The WeasyPrint plumbing — the macOS loader shim, the fetcher that resolves
/static/ off disk and remote images through `requests`, the file:// base URL
— now lives in erp/pdf_render.py, which every rendered document shares. What
stays here is the catalog's own: the AVIF check its product photos need and
the downscaling that keeps a seven-page catalog mailable.
"""
from __future__ import annotations

import logging

from django.conf import settings

from erp import pdf_render

logger = logging.getLogger(__name__)

# Product photos are AVIF on the CDN. Pillow only decodes AVIF natively from
# 11.3 onwards — on an older Pillow every image silently renders as a blank
# box, so fail loudly at render time instead (see check_image_support).
_AVIF_HINT = (
    "Product images are AVIF; this Pillow cannot decode them. "
    "Upgrade Pillow (>=11.3) or install pillow-avif-plugin."
)


def check_image_support():
    """True if Pillow can decode the AVIF product photos.

    Two ways to get there: Pillow >= 11.3 decodes AVIF natively, older ones
    need pillow-avif-plugin, which registers the codec purely as an import
    side effect (erp.image_optimizer imports it the same way).
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
    """Filesystem path for a /static/… URL — see erp.pdf_render."""
    return pdf_render.static_path(url)


def url_fetcher(url: str):
    """The shared fetcher, with the catalog's photo downscaling wired in."""
    return pdf_render.url_fetcher(url, image_hook=_downscale)


def _downscale(raw: bytes, content_type: str | None):
    """Shrink a source photo to print resolution before embedding.

    WeasyPrint embeds whatever pixels it is given. The CDN originals are
    full-resolution, which made a ONE-page catalog a 9.6MB PDF — a 7-page one
    would have been unmailable. The PRINT profile (erp.image_optimizer) is
    visually lossless at 62mm wide and cuts the file by ~50x. A photo it
    cannot process is better embedded as-is than dropped.
    """
    from erp.image_optimizer import PRINT, OptimizedImage, optimize_image

    out = optimize_image(raw, PRINT)
    if isinstance(out, OptimizedImage):
        return {"string": out.getvalue(), "mime_type": out.content_type}
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


def render_catalog_pdf(html: str, base_url: str | None = None) -> bytes:
    """Rendered catalog HTML → PDF bytes."""
    if not check_image_support():
        logger.warning(_AVIF_HINT)

    return pdf_render.render_pdf(html, base=base_url, image_hook=_downscale)


# Registers the AVIF codec up front, so _downscale() can decode product photos
# even when the fetcher is driven outside render_catalog_pdf().
check_image_support()
