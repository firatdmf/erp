"""Catalog PDF — preview and download views.

Reproduces page 1 of the reference DEMFIRAT catalog, which proved out the
renderer: fonts + Turkish glyphs, AVIF photos off the CDN, page geometry,
footer bar, QR. The COPY here is hardcoded on purpose — _sample_pages() is
throwaway and gets replaced with real Product/ProductVariant data, while the
template and CSS stay exactly as they are.

Photos are pulled from real products so this exercises the actual image
pipeline (remote AVIF → requests → Pillow → WeasyPrint) rather than a local
placeholder that would prove nothing.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string

from .catalog_builder import Pricing, build_pages, catalog_queryset
from .catalog_pdf import check_image_support, read_catalog_css, render_catalog_pdf

logger = logging.getLogger(__name__)


def _qr_svg(url: str) -> str:
    """Inline SVG QR for the footer (segno — already a project dependency)."""
    try:
        import io
        import segno
        buffer = io.BytesIO()
        segno.make(url, error="m").save(
            buffer, kind="svg", xmldecl=False, svgns=True, scale=4, border=0,
            dark="#6d4c33",
        )
        return buffer.getvalue().decode("utf-8")
    except Exception:
        logger.exception("catalog QR generation failed")
        return ""


def _sample_photos(count: int):
    """A few real CDN image URLs, to exercise remote AVIF decoding."""
    from .models import ProductFile
    urls = list(
        ProductFile.objects
        .filter(file_type="image")
        .exclude(file_url__isnull=True).exclude(file_url="")
        .values_list("file_url", flat=True)[:count]
    )
    urls += [None] * (count - len(urls))
    return urls


def _sample_pages():
    """Page 1 of the reference catalog, verbatim. Placeholder for real data."""
    photos = _sample_photos(3)
    ranforce = "80% Cotton, 20% Polyester, 57-strand Ranforce"

    return [{
        "kicker": "CATALOG",
        "section": "BEDDING",
        "meta_top": "HOME TEXTILES",
        "meta_bottom": "JULY 2026",
        "show_masthead": True,
        "blocks": [
            {
                "kind": "list",
                "title": "Fitted Bed Sheet",
                "spec": ranforce,
                "photo": photos[0],
                "photo_side": "left",
                "rows": [
                    {"label": "100 x 200 + 20 cm", "amount": "€2.00"},
                    {"label": "120 x 200 + 20 cm", "amount": "€2.45"},
                    {"label": "160 x 200 + 20 cm", "amount": "€2.80"},
                    {"label": "180 x 200 + 20 cm", "amount": "€3.00"},
                    {"label": "200 x 200 + 20 cm", "amount": "€3.30"},
                ],
            },
            {
                "kind": "list",
                "title": "Fitted Bed Sheet with Pillow Case(s)",
                "spec": ranforce,
                "photo": photos[1],
                "photo_side": "right",
                "rows": [
                    {"label": "100 x 200 + 20 cm with 1 Pillow Case", "amount": "€2.80"},
                    {"label": "120 x 200 + 20 cm with 1 Pillow Case", "amount": "€3.00"},
                    {"label": "160 x 200 + 20 cm with 2 Pillow Cases", "amount": "€4.00"},
                    {"label": "180 x 200 + 20 cm with 2 Pillow Cases", "amount": "€4.25"},
                    {"label": "200 x 200 + 20 cm with 2 Pillow Cases", "amount": "€4.50"},
                ],
            },
            {
                "kind": "set",
                "title": "Bedding Set",
                "spec": ranforce,
                "photo": photos[2],
                "photo_side": "left",
                "columns": [
                    {
                        "heading": "Single Size",
                        "amount": "€7",
                        "rows": [
                            "1 Quilt Cover (160 x 220 cm)",
                            "1 Fitted Sheet (100 x 200 cm)",
                            "1 Pillow Case (50x70 cm)",
                        ],
                    },
                    {
                        "heading": "Double Size",
                        "amount": "€9",
                        "rows": [
                            "1 Quilt Cover (200 x 220 cm)",
                            "1 Fitted Sheet (160 x 200 cm)",
                            "2 Pillow Cases (50x70 cm)",
                        ],
                    },
                ],
            },
        ],
    }]


def _context(request=None):
    """Template context.

    ?sample=1 renders the hand-written reference page instead of live data —
    handy for checking the LAYOUT without a database, and the fixture the
    design was built against. Everything else comes from real products.
    """
    website = "www.demfirat.com"
    request_get = request.GET if request is not None else {}

    if request_get.get("sample"):
        pages = _sample_pages()
    else:
        products = catalog_queryset(
            limit=int(request_get.get("limit") or 0) or None,
            order=request_get.get("order") or "title",
            category=request_get.get("category") or "",
        )
        markup = request_get.get("markup")
        pages = build_pages(
            products,
            section=(request_get.get("section") or "").upper(),
            meta_bottom=request_get.get("period") or "",
            # No ?markup= keeps the price stored on each variant. With one,
            # every line is re-derived from cost at that single rate.
            pricing=Pricing(
                currency=request_get.get("currency") or "USD",
                markup=markup if markup not in (None, "") else None,
            ),
        )

    return {
        "page_title": "Catalog",
        "catalog_css": read_catalog_css(),
        "brand": {
            "name": getattr(settings, "BRAND_NAME", "") or "Demfirat",
            "collection": "Karven Home Collection",
            "website": website,
            "qr_svg": _qr_svg(f"https://{website}"),
        },
        "pages": pages,
    }


@login_required
def catalog_preview(request):
    """The catalog as HTML — iterate here, it renders in milliseconds."""
    context = _context(request)
    return HttpResponse(render_to_string("marketing/catalog/page.html", context, request=request))


@login_required
def catalog_download(request):
    """The same template through WeasyPrint."""
    if not check_image_support():
        logger.warning("Pillow cannot decode AVIF — catalog photos will be blank")

    html = render_to_string("marketing/catalog/page.html", _context(request), request=request)
    pdf = render_catalog_pdf(html)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="catalog.pdf"'
    return response
