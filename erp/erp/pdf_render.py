"""A printable HTML document → a real PDF, with WeasyPrint.

Every document in here used to be served as styled HTML that opened the
browser's print dialog, leaving the reader to choose "Save as PDF". That
works, but what comes out is the BROWSER's: Chrome stamps its own URL and
page number across the margins unless the reader turns them off, Safari
paginates differently, and a phone gives nothing useful at all. So what
the customer receives depended on who pressed Ctrl+P.

This renders the same template server-side instead — one PDF, the same
for everyone, opening in a tab the way the packing list always has.

It is the CSS engine that lays the page out, not hand-placed reportlab
coordinates: these documents are cards, chips and tinted table heads, and
a design authored in HTML is one we can keep editing in HTML. reportlab
still draws what is genuinely coordinate work — warehouse labels, the
pack QR sheets, the packing list.

Where a host cannot render (WeasyPrint needs Pango as a SYSTEM library),
`document_response` falls back to serving the HTML with its print dialog.
A document that degrades to the old behaviour beats a 500 on the page
somebody is trying to hand to a customer.

The plumbing below — the macOS loader shim, resolving /static/ off disk —
came from marketing/catalog_pdf.py, which was the first WeasyPrint
document here and now shares it rather than keeping its own copy.
"""
from __future__ import annotations

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


def ensure_dyld_path():
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


def static_path(url: str):
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


def url_fetcher(url: str, image_hook=None):
    """WeasyPrint fetcher: statics off disk, remote images via requests.

    WeasyPrint's own fetcher is urllib, which does not use certifi — every
    https image then fails with CERTIFICATE_VERIFY_FAILED on macOS. Going
    through `requests` also gives us a timeout, so one unreachable image
    cannot hang the worker rendering somebody's invoice.

    `image_hook` gets (bytes, content_type) for anything image/* and
    returns the dict to embed instead — the catalog uses it to downscale
    full-resolution photos. A document of type and rules needs none.
    """
    if url.startswith("data:"):
        from weasyprint import default_url_fetcher
        return default_url_fetcher(url)

    path = static_path(url)
    if path:
        return {"file_obj": open(path, "rb")}

    if url.startswith(("http://", "https://")):
        import requests
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";")[0] or None
        if image_hook and (content_type or "").startswith("image/"):
            return image_hook(response.content, content_type)
        return {"string": response.content, "mime_type": content_type}

    from weasyprint import default_url_fetcher
    return default_url_fetcher(url)


def base_url() -> str:
    """A real file:// URL for resolving a document's relative references.

    Must be a URL, not a bare filesystem path: given a path with no scheme
    WeasyPrint silently ignores it, and every "/static/…" reference —
    including any @font-face — is dropped without so much as a warning.
    """
    from pathlib import Path
    return Path(settings.BASE_DIR).as_uri() + "/"


def render_pdf(html: str, base=None, image_hook=None) -> bytes:
    """Rendered HTML → PDF bytes. Raises if this host cannot render."""
    ensure_dyld_path()
    from weasyprint import HTML

    return HTML(
        string=html,
        base_url=base or base_url(),
        url_fetcher=(lambda url: url_fetcher(url, image_hook=image_hook)),
    ).write_pdf()


def document_response(request, template, context, filename, download=False):
    """Serve a printable template as a PDF, or as HTML if we cannot.

    `is_pdf` is set for the PDF pass, which is what keeps the template's
    auto-print script out of it — that script exists for the HTML
    fallback, where the reader still saves the file from the browser.

    Served inline: it opens in a tab, which is how a document meant for
    reading (and then handing on) should arrive. `download=True` for the
    few that are only ever saved.

    Add ?html=1 to any of these addresses to get the page itself. That is
    how you iterate on the design — the same template, no render step —
    and it is also the escape hatch if a PDF ever comes out wrong.
    """
    from django.http import HttpResponse
    from django.template.loader import render_to_string

    def html_fallback():
        # is_pdf False: the template opens the browser's print dialog.
        page = render_to_string(template, {**context, "is_pdf": False},
                                request=request)
        return HttpResponse(page)

    if request.GET.get("html"):
        return html_fallback()

    try:
        html = render_to_string(template, {**context, "is_pdf": True},
                                request=request)
        pdf = render_pdf(html)
    except Exception:
        # A host without Pango, or a template that WeasyPrint chokes on.
        # Logged loudly — this is meant to be the rare path — and the
        # reader still gets their document.
        logger.exception("PDF render failed for %s; serving HTML", template)
        return html_fallback()

    response = HttpResponse(pdf, content_type="application/pdf")
    disposition = "attachment" if download else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response


ensure_dyld_path()
