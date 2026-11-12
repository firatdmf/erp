"""Printable roll/variant labels (PDF) for warehouse products.

Re-creates the physical fabric-roll sticker: the business's name, DESEN (main
product) + VARYANT, SKU, METRE, a Code128 barcode and a QR code — one label
per stock item (each carries its own barcode + quantity), so staff can reprint and
stick a fresh label on a product.

Uses reportlab (Code128) + segno (QR) — both already in the project, no new
deps — and the bundled DejaVu Sans so Turkish characters (GÜMÜŞ, K48083İ)
render instead of boxes.
"""
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from erp.branding import brand as brand_value
from marketing import units

from .models import Warehouse, WarehouseProduct


def warehouse_product_info(request, warehouse_pk, product_pk):
    """Clean, label-style read-only info screen — what the QR opens when
    scanned. PUBLIC (no login) so anyone scanning a physical label can see
    the product. Brand + DESEN/VARYANT/SKU/METRE + barcode, mobile-friendly.
    Admin actions on the page stay behind login."""
    from .catalog_sync import derive_catalog
    product = get_object_or_404(WarehouseProduct, pk=product_pk, warehouse_id=warehouse_pk)
    cat = derive_catalog(product.sku, product.name)
    return render(request, "operating/warehouse_product_info.html", {
        "product": product,
        "base": cat["base_name"] or product.name,
        "variant": cat["original_token"] or "",
        "brand": brand_value("BRAND_NAME") or "Nejum",
    })


def label_brand(request):
    """The name a label prints, as its print button's menu picked it:
    None for each label's own business (the book that holds the stock),
    "" for white label — no name at all — or the custom name typed in."""
    if request.GET.get("white_label"):
        return ""
    return (request.GET.get("brand") or "").strip() or None


def _label_pdf_bytes(product, rolls, detail_url=None, title=None, brand=None):
    """One product's labels: a page per roll, or a single product-level
    page when it has none."""
    return labels_pdf_bytes([(product, r) for r in rolls] or [(product, None)],
                            detail_url=detail_url, title=title, brand=brand)


def labels_pdf_bytes(pairs, detail_url=None, title=None, brand=None):
    """A label sheet for (product, roll) pairs — one page each, in order.

    Pairs rather than one product plus its rolls, because a caller like the
    purchase-order page prints the rolls of a whole delivery line, and those
    can sit on more than one warehouse product; every page has to carry its
    own roll's product name and SKU — and its own business's name, taken
    from the book of the warehouse the roll stands in, unless ``brand``
    (see label_brand) says otherwise.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.graphics.barcode import code128
    import segno
    from PIL import Image

    from accounting.services_accounts import brand_name_for

    from .catalog_sync import derive_catalog
    from .order_notifications import (LABEL_BRAND_TRACKING, _ensure_pdf_fonts,
                                      brand_width, draw_brand)

    reg = _ensure_pdf_fonts() or "Helvetica"
    bold = "Helvetica-Bold" if reg == "Helvetica" else f"{reg}-Bold"
    # Captions in Medium: lighter than the bold values, so the two read
    # apart, yet solid on the printer's dots, where regular broke up.
    caption = "Helvetica" if reg == "Helvetica" else f"{reg}-Medium"
    names = {}  # warehouse id → its business's name

    # The sticker's own size, 66 × 44 mm, in Ergene and Laleli alike. Drawn
    # any bigger, the print dialog shrank it to fit — to 76% when this was
    # 76 × 58 — and on a thermal printer's 8 dots a millimetre the small
    # words broke up ("SKU" printed as "SKLI") and the brand's letters
    # rounded unevenly. Drawn at size, nothing is scaled.
    W, H, M = 66 * mm, 44 * mm, 3 * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    # PDF metadata → browser tab title when opened inline.
    if title:
        c.setTitle(title)
        c.setSubject(title)

    def fit(text, font, size, width, smallest):
        """`text` at `size`, shrunk toward `smallest` until it fits
        `width`, then cut with "…": (text, size)."""
        text = str(text)
        while size > smallest and c.stringWidth(text, font, size) > width:
            size -= 0.25
        if c.stringWidth(text, font, size) > width:
            while text and c.stringWidth(text + "…", font, size) > width:
                text = text[:-1]
            text += "…"
        return text, size

    for product, roll in pairs:
        cat = derive_catalog(product.sku, product.name)
        base = cat["base_name"] or product.name or "—"
        token = cat["original_token"] or ""
        sku = product.sku or ""
        bc_val = (roll.barcode if (roll and roll.barcode) else (product.barcode or sku or ""))
        # What is physically on the stock item NOW, not what it arrived
        # at: a cut roll carries quantity_remaining, and the reprinted label
        # goes back on that shorter roll. quantity_remaining is null for a
        # stock item that has never been cut, so fall back to the full
        # quantity there.
        if roll is not None:
            quantity = (roll.quantity_remaining
                        if roll.quantity_remaining is not None else roll.quantity)
        else:
            quantity = product.quantity
        quantity = quantity or 0

        # ── QR (top-right) — encodes the ROLL barcode so a QR scan flows
        #    through the same warehouse-lookup pipeline as a 1D scan. QRs
        #    are physically more reliable to scan than Code128, especially
        #    on tags that get folded/scuffed. Falls back to product-level
        #    identifiers if there's no roll (SKU/name), then to detail_url
        #    as a last resort so the QR is never empty. ──
        qr_val = bc_val or sku or (product.name or "") or detail_url
        qsize = 15 * mm
        if qr_val:
            qbuf = BytesIO()
            segno.make(str(qr_val), error="m").save(qbuf, kind="png", scale=8)
            qbuf.seek(0)
            c.drawInlineImage(Image.open(qbuf).convert("RGB"),
                              W - M - qsize, H - M - qsize, qsize, qsize)

        # ── Brand: the business the roll belongs to ──
        name = brand
        if name is None:
            if product.warehouse_id not in names:
                names[product.warehouse_id] = brand_name_for(product.warehouse.accounting_book)
            name = names[product.warehouse_id]
        second = roll and getattr(roll, 'is_second', False)
        tag = "2ND QUALITY"
        pad = 1.2 * mm
        brand_y = H - M - 3.6 * mm
        # Across the top, left of the QR.
        room = W - 2 * M - qsize - 3 * mm
        if name:
            size = 10
            while size > 6 and brand_width(name, bold, size, LABEL_BRAND_TRACKING) > room:
                size -= 0.25
            if brand_width(name, bold, size, LABEL_BRAND_TRACKING) > room:
                while name and brand_width(name + "…", bold, size, LABEL_BRAND_TRACKING) > room:
                    name = name[:-1]
                name += "…"
            draw_brand(c, M, brand_y, name, bold, size, LABEL_BRAND_TRACKING)

        # ── One baseline for the rows: the SKU row sits just above the
        #    barcode, the fields stack upward from it, and QUANTITY stands
        #    on the SKU row — caption beside caption, value beside value.
        #    Placed from the QR down and the brand down, the two columns'
        #    lines never met. ──
        row = 7.2 * mm                 # caption to the next caption
        sku_y = 18 * mm                # the SKU row's caption baseline

        # ── "2nd" badge — a factory second says so under the QR, right-
        #    aligned over the quantity. Beside the brand it cut the
        #    business's name short. ──
        if second:
            c.setFont(bold, 5.5)
            tw = c.stringWidth(tag, bold, 5.5)
            bx, by = W - M - tw - 2 * pad, sku_y + 4 * mm
            c.roundRect(bx, by - 1 * mm, tw + 2 * pad, 3.2 * mm, 0.8 * mm, stroke=1, fill=0)
            c.drawString(bx + pad, by, tag)

        # ── QUANTITY (right, on the SKU row) — the stack beside it stops
        #    short of it ──
        # "80 pcs" for a count, "19.70 m" for cloth — as the pack label.
        amount = units.format_amount(quantity, product.unit)
        amount_w = c.stringWidth(amount, bold, 11)
        c.setFont(caption, 5.5)
        c.drawRightString(W - M, sku_y, "QUANTITY")
        c.setFont(bold, 11)
        c.drawRightString(W - M, sku_y - 3.6 * mm, amount)

        # ── Field stack (left): a small caption over its value — the
        #    caption in Medium, the value bold. ──
        value_room = W - 2 * M - max(amount_w, qsize) - 3 * mm

        def field(label, value, y):
            c.setFont(caption, 5.5)
            c.drawString(M, y, label)
            text, size = fit(value, bold, 9, value_room, 6.5)
            c.setFont(bold, size)
            c.drawString(M, y - 3.6 * mm, text)

        rows = [("PRODUCT", base)] + ([("VARIANT", token)] if token else []) + [("SKU", sku or "—")]
        for i, (label, value) in enumerate(rows):
            field(label, value, sku_y + (len(rows) - 1 - i) * row)

        # ── Code128 barcode (bottom, auto-shrunk to fit). Three dots a bar
        #    (0.375 mm) when it fits, so every bar is whole dots wide. ──
        if bc_val:
            maxw = W - 2 * M
            bw = 0.375 * mm
            bc = code128.Code128(str(bc_val), barHeight=6.5 * mm, barWidth=bw)
            if bc.width > maxw:
                bc = code128.Code128(str(bc_val), barHeight=6.5 * mm,
                                     barWidth=bw * maxw / bc.width)
            bc.drawOn(c, (W - bc.width) / 2, 4.8 * mm)
            # The digits under the bars, legible on a scuffed sticker when
            # the scanner can't read the bars.
            c.setFont(bold, 8)
            c.drawCentredString(W / 2, 1.9 * mm, str(bc_val))

        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def warehouse_product_code(request, warehouse_pk, product_pk):
    """Return a QR (segno, PNG) or Code128 barcode (reportlab, SVG) image.
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
        # SVG, not PNG: rasterising a reportlab drawing goes through
        # renderPM, which needs rlPyCairo → pycairo → system libcairo.
        # That dependency is deliberately kept out of requirements.txt
        # (it breaks the Nixpacks build), so asString("png") raised
        # "cannot import desired renderPM backend rlPyCairo" and the
        # barcode <img> rendered broken while the QR (pure-python segno)
        # loaded fine. renderSVG is pure python and scales crisply.
        return HttpResponse(d.asString("svg"), content_type="image/svg+xml")

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
    ?stock_item=<pk> for a single roll's label."""
    warehouse = get_object_or_404(Warehouse, pk=warehouse_pk)
    product = get_object_or_404(WarehouseProduct, pk=product_pk, warehouse=warehouse)

    roll_pk = (request.GET.get("roll") or "").strip()
    if roll_pk.isdigit():
        # An explicitly named roll always prints, consumed or not — asking
        # for one specific label is asking for that label.
        rolls = list(product.stock_items.filter(pk=int(roll_pk)))
    else:
        # Print what the product page shows: fully-consumed rolls are hidden
        # there (WarehouseProductDetail excludes them), so they can't be
        # corrected from the UI either — yet they were still coming out of
        # the printer, carrying whatever barcode they were retired with.
        # A label for a roll that no longer physically exists has nothing
        # to be stuck on.
        rolls = list(product.stock_items.exclude(status="consumed").order_by("id"))

    from django.urls import reverse
    detail_url = request.build_absolute_uri(reverse(
        "operating:warehouse_product_info",
        kwargs={"warehouse_pk": warehouse_pk, "product_pk": product_pk}))

    # Build a meaningful title (browser tab) and safe filename (download).
    product_name = (product.name or product.sku or f"Product {product.pk}").strip()
    if len(rolls) == 1 and rolls[0].barcode:
        title = f"Label — {product_name} — {rolls[0].barcode}"
        stem = f"label-{product.sku or product.pk}-{rolls[0].barcode}"
    else:
        title = f"Label — {product_name}"
        stem = f"label-{product.sku or product.pk}"
    pdf = _label_pdf_bytes(product, rolls, detail_url=detail_url, title=title,
                           brand=label_brand(request))
    return inline_pdf_response(pdf, stem)


def inline_pdf_response(pdf, stem):
    """A label PDF the browser opens in a tab, named so it can be saved.

    RFC 5987 filename* carries the full Unicode (Turkish chars preserved
    in modern browsers), plus an ASCII-transliterated filename= fallback
    for older clients. Turkish İ → I via NFKD so the fallback stays
    readable instead of dropping the letter.
    """
    import re
    import unicodedata
    from urllib.parse import quote
    ascii_stem = (
        unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    )
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_stem).strip("-") or "label"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'inline; filename="{ascii_stem}.pdf"; '
        f"filename*=UTF-8''{quote(stem + '.pdf')}"
    )
    return resp
