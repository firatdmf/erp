"""Printable roll/variant labels (PDF) for warehouse products.

Re-creates the physical fabric-roll sticker: brand wordmark, DESEN (main
product) + VARYANT, SKU, METRE, a Code128 barcode and a QR code — one label
per roll (each roll has its own barcode + meters), so staff can reprint and
stick a fresh label on a product.

Uses reportlab (Code128) + segno (QR) — both already in the project, no new
deps — and the bundled DejaVu Sans so Turkish characters (GÜMÜŞ, K48083İ)
render instead of boxes.
"""
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Warehouse, WarehouseProduct


def warehouse_product_info(request, warehouse_pk, product_pk):
    """Clean, label-style read-only info screen — what the QR opens when
    scanned. PUBLIC (no login) so anyone scanning a physical label can see
    the product. Brand + DESEN/VARYANT/SKU/METRE + barcode, mobile-friendly.
    Admin actions on the page stay behind login."""
    from django.conf import settings
    from .catalog_sync import derive_catalog
    product = get_object_or_404(WarehouseProduct, pk=product_pk, warehouse_id=warehouse_pk)
    cat = derive_catalog(product.sku, product.name)
    return render(request, "operating/warehouse_product_info.html", {
        "product": product,
        "base": cat["base_name"] or product.name,
        "variant": cat["original_token"] or "",
        "brand": (getattr(settings, "BRAND_NAME", "") or "Nejum"),
    })


def _label_pdf_bytes(product, rolls, detail_url=None, title=None):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
    from django.conf import settings
    import segno
    from PIL import Image

    from .catalog_sync import derive_catalog
    from .order_notifications import _ensure_pdf_fonts

    reg = _ensure_pdf_fonts() or "Helvetica"
    bold = "DejaVuSans-Bold" if reg == "DejaVuSans" else "Helvetica-Bold"

    cat = derive_catalog(product.sku, product.name)
    base = cat["base_name"] or product.name or "—"
    token = cat["original_token"] or ""
    brand = (getattr(settings, "BRAND_NAME", "") or "Nejum").upper()
    sku = product.sku or ""

    W, H = 76 * mm, 58 * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    # PDF metadata → browser tab title when opened inline.
    if title:
        c.setTitle(title)
        c.setSubject(title)

    # One label per roll; if there are no rolls, one product-level label.
    items = list(rolls) if rolls else [None]
    for roll in items:
        bc_val = (roll.barcode if (roll and roll.barcode) else (product.barcode or sku or ""))
        meters = (roll.meters if roll else product.quantity) or 0

        # ── QR (top-right) — encodes the ROLL barcode so a QR scan flows
        #    through the same warehouse-lookup pipeline as a 1D scan. QRs
        #    are physically more reliable to scan than Code128, especially
        #    on tags that get folded/scuffed. Falls back to product-level
        #    identifiers if there's no roll (SKU/name), then to detail_url
        #    as a last resort so the QR is never empty. ──
        qr_val = bc_val or sku or (product.name or "") or detail_url
        qsize = 21 * mm
        if qr_val:
            qbuf = BytesIO()
            segno.make(str(qr_val), error="m").save(qbuf, kind="png", scale=8)
            qbuf.seek(0)
            c.drawInlineImage(Image.open(qbuf).convert("RGB"),
                              W - qsize - 4 * mm, H - qsize - 4 * mm, qsize, qsize)

        # ── Brand ──
        c.setFillColorRGB(0.58, 0.31, 0.02)
        c.setFont(bold, 12)
        c.drawString(4 * mm, H - 9 * mm, brand)
        c.setFillColorRGB(0, 0, 0)

        # ── Field stack (left) ──
        def field(label, value, y):
            c.setFont(reg, 6.5)
            c.setFillColorRGB(0.42, 0.42, 0.42)
            c.drawString(4 * mm, y, label)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(bold, 9)
            c.drawString(4 * mm, y - 4.4 * mm, str(value)[:26])
            return y - 9.2 * mm

        y = H - 15 * mm
        y = field("DESEN", base, y)
        if token:
            y = field("VARYANT", token, y)
        y = field("SKU", sku or "—", y)

        # ── METRE (right, under the QR) ──
        c.setFont(reg, 6.5)
        c.setFillColorRGB(0.42, 0.42, 0.42)
        c.drawRightString(W - 4 * mm, H - qsize - 8 * mm, "METRE")
        c.setFillColorRGB(0, 0, 0)
        c.setFont(bold, 12)
        c.drawRightString(W - 4 * mm, H - qsize - 13.5 * mm, f"{float(meters):.2f}")

        # ── Code128 barcode (bottom, auto-shrunk to fit) ──
        if bc_val:
            maxw = W - 8 * mm
            bw = 0.45 * mm
            bc = code128.Code128(str(bc_val), barHeight=8.5 * mm, barWidth=bw)
            if bc.width > maxw:
                bc = code128.Code128(str(bc_val), barHeight=8.5 * mm,
                                     barWidth=bw * maxw / bc.width)
            bc.drawOn(c, (W - bc.width) / 2, 4.5 * mm)
            c.setFont(reg, 7)
            c.drawCentredString(W / 2, 1.6 * mm, str(bc_val))

        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def warehouse_product_code(request, warehouse_pk, product_pk):
    """Return a QR (segno) or Code128 barcode (reportlab) PNG for a product.
    PUBLIC (no login) so the codes load on the public info page too.
    ?kind=qr (default) | barcode
    """
    product = get_object_or_404(WarehouseProduct, pk=product_pk, warehouse_id=warehouse_pk)
    value = product.barcode or product.sku or product.name or str(product.pk)
    kind = (request.GET.get("kind") or "qr").lower()

    if kind == "barcode":
        from reportlab.graphics.barcode import createBarcodeDrawing
        d = createBarcodeDrawing("Code128", value=str(value), barHeight=42,
                                 barWidth=1.1, humanReadable=True)
        return HttpResponse(d.asString("png"), content_type="image/png")

    # QR encodes the clean info-screen URL so scanning opens the label-style
    # product info page on the phone (not just the raw barcode text).
    from django.urls import reverse
    url = request.build_absolute_uri(reverse(
        "operating:warehouse_product_info",
        kwargs={"warehouse_pk": warehouse_pk, "product_pk": product_pk}))
    import segno
    buf = BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=8, border=2)
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
def warehouse_product_label(request, warehouse_pk, product_pk):
    """Inline PDF of printable labels for a product (one per roll). Pass
    ?roll=<pk> for a single roll's label."""
    warehouse = get_object_or_404(Warehouse, pk=warehouse_pk)
    product = get_object_or_404(WarehouseProduct, pk=product_pk, warehouse=warehouse)

    roll_pk = (request.GET.get("roll") or "").strip()
    if roll_pk.isdigit():
        rolls = list(product.rolls.filter(pk=int(roll_pk)))
    else:
        rolls = list(product.rolls.all().order_by("id"))

    from django.urls import reverse
    detail_url = request.build_absolute_uri(reverse(
        "operating:warehouse_product_info",
        kwargs={"warehouse_pk": warehouse_pk, "product_pk": product_pk}))

    # Build a meaningful title (browser tab) and safe filename (download).
    import re
    product_name = (product.name or product.sku or f"Product {product.pk}").strip()
    if len(rolls) == 1 and rolls[0].barcode:
        title = f"Label — {product_name} — {rolls[0].barcode}"
        stem = f"label-{product.sku or product.pk}-{rolls[0].barcode}"
    else:
        title = f"Label — {product_name}"
        stem = f"label-{product.sku or product.pk}"
    # Filename: RFC 5987 filename* carries the full Unicode (Turkish
    # chars preserved in modern browsers), plus an ASCII-transliterated
    # filename= fallback for older clients. Turkish İ → I via NFKD so
    # the fallback stays readable instead of dropping the letter.
    import unicodedata
    from urllib.parse import quote
    ascii_stem = (
        unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    )
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_stem).strip("-") or "label"

    pdf = _label_pdf_bytes(product, rolls, detail_url=detail_url, title=title)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'inline; filename="{ascii_stem}.pdf"; '
        f"filename*=UTF-8''{quote(stem + '.pdf')}"
    )
    return resp
