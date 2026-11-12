"""Mini packing list for the outside of a package, on the 66 × 44 mm
sticker the thermal label printers take in Ergene and Laleli: the page is
that size, so nothing is scaled to fit, and the label stands up in it
(44 × 66), one label per page.

The order's brand (or none, or another name, as printed), the order number and
"package 3 / 7" beside a QR that
opens this package on the order's packing list, and what is inside, one
line per SKU ("4 rolls · 212.50 m") — rolls of one SKU are added up,
since a label this size can't list every roll. A package with more SKUs
than fit carries on onto a second label, marked 2/2, rather than cutting
anything off.
"""
from io import BytesIO

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _

from marketing import units

from .models import Order, Pack
from .split_orders import combined_number, half_number, order_packs, split_halves
from .warehouse_label import inline_pdf_response, label_brand

LINES_PER_LABEL = 8


def _pack_lines(pack):
    """The package's contents added up per SKU, in the order first packed:
    [{"sku", "unit", "pack_type", "tracking", "items", "quantity"}]."""
    from .views import _pack_roll_rows

    lines = {}
    for row in _pack_roll_rows(pack):
        line = lines.setdefault(row["sku"], {
            "sku": row["sku"], "unit": row["unit"], "pack_type": row["pack_type"],
            "tracking": row["tracking"], "items": 0, "quantity": 0})
        line["items"] += 1
        line["quantity"] += row["quantity"] or 0
    return list(lines.values())


def _amount(quantity, unit):
    """"212.50 m", or "22 pcs" for a count."""
    if unit in units.WHOLE_UNITS and quantity == int(quantity):
        number = f"{int(quantity):,}"
    else:
        number = f"{quantity:,.2f}"
    return f"{number} {units.unit_short(unit)}"


def _describe(items, quantity, unit, pack_type, tracking):
    """"4 rolls · 212.50 m". Goods tracked by variant are just their count:
    the stock entries behind "22 pcs" are batches, not boxes anyone can find."""
    amount = _amount(quantity, unit)
    if units.by_variant(tracking) or not units.counts_packs(pack_type):
        return amount
    return f"{items} {units.pack_noun(pack_type, items)} · {amount}"


def _total(lines):
    """Every unit in the package added up — "9 rolls · 512.30 m · 22 pcs"."""
    by_unit = {}
    for line in lines:
        key = (line["unit"], line["tracking"])
        total = by_unit.setdefault(key, {"items": 0, "quantity": 0,
                                         "pack_type": line["pack_type"]})
        total["items"] += line["items"]
        total["quantity"] += line["quantity"]
        if total["pack_type"] != line["pack_type"]:
            total["pack_type"] = None  # rolls and bales don't add up to one noun
    parts = []
    for (unit, tracking), t in by_unit.items():
        if t["pack_type"] is None and not units.by_variant(tracking):
            parts.append(_amount(t["quantity"], unit))
        else:
            parts.append(_describe(t["items"], t["quantity"], unit, t["pack_type"], tracking))
    return " · ".join(parts)


def labels_pdf_bytes(packs, title, link=None, brand=None):
    """Labels for these packages of one order, a page each (more for a
    package that runs over LINES_PER_LABEL SKUs). ``link(pack)`` is what
    the QR opens; without one it holds just the package code. ``brand``
    is warehouse_label.label_brand's choice: None for the order's book."""
    import segno
    from PIL import Image
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from accounting.services_accounts import brand_name_for

    from .order_notifications import (LABEL_BRAND_TRACKING, _ensure_pdf_fonts,
                                      brand_width, draw_brand)

    reg = _ensure_pdf_fonts() or "Helvetica"
    bold = "Helvetica-Bold" if reg == "Helvetica" else f"{reg}-Bold"
    # Captions in Medium: lighter than the bold values, so the two read
    # apart, yet solid on the printer's dots, where regular broke up.
    caption = "Helvetica" if reg == "Helvetica" else f"{reg}-Medium"

    # The printer takes the 66 × 44 mm roll, so that is the page — any
    # other size and the print dialog scales it. The label stands up in it,
    # 44 wide and 66 tall, drawn turned a quarter: standing, a package's
    # products fit a line each, up to eight to a sticker, where lying
    # down took three. The sticker is turned when it goes on.
    W, H = 66 * mm, 44 * mm
    PW, PH, M = 44 * mm, 66 * mm, 3 * mm
    qsize = 13 * mm
    BRAND_BAND = 5 * mm     # the brand line's share of the top
    ROW = 3.7 * mm          # one product line to the next
    UNDER = 2.6 * mm        # a long code's amount, on the line under it
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(title)

    def fit(text, font, size, width):
        if c.stringWidth(text, font, size) <= width:
            return text
        while text and c.stringWidth(text + "…", font, size) > width:
            text = text[:-1]
        return text + "…"

    def shrink(text, font, size, width, smallest):
        while size > smallest and c.stringWidth(text, font, size) > width:
            size -= 0.25
        return size

    for pack in packs:
        order = pack.order
        # The book the order's money posts to, so each sack carries the
        # name of the business that sold what is in it — unless the print
        # button's menu picked white label ("") or a custom name.
        name = brand if brand is not None else brand_name_for(
            order.current_account.book if order.current_account_id else None)
        # A split order's packages are one run across its halves, and a
        # sack may hold either half's goods: the label names both.
        halves = split_halves(order)
        of = order_packs(order).count()
        lines = _pack_lines(pack)
        total = _total(lines)
        # Each product on one line — its code left, what of it is inside
        # right, on one baseline — at a size that fits; a code too long for
        # that takes two lines, the amount under it. Then as many as the
        # sticker holds, up to LINES_PER_LABEL, the rest on the next.
        top = PH - M - (BRAND_BAND if name else 0)
        first = top - qsize - 1.4 * mm - 3.2 * mm   # first row's baseline
        lowest = 7.8 * mm                           # last baseline, over the total
        rows = []
        for line in lines:
            amount = _describe(line["items"], line["quantity"], line["unit"], line["pack_type"],
                               line["tracking"])
            size, single = 7.5, False
            while size >= 6.5:
                if (c.stringWidth(line["sku"], bold, size) + 2 * mm
                        + c.stringWidth(amount, reg, size)) <= PW - 2 * M:
                    single = True
                    break
                size -= 0.25
            rows.append({"sku": line["sku"], "amount": amount,
                         "size": size if single else 7.5, "single": single})
        pages, page, y = [], [], first
        for row in rows:
            depth = 0 if row["single"] else UNDER
            if page and (len(page) == LINES_PER_LABEL or y - depth < lowest):
                pages.append(page)
                page, y = [], first
            page.append(row)
            y -= ROW if row["single"] else ROW + UNDER
        pages.append(page)

        qbuf = BytesIO()
        segno.make(link(pack) if link else (pack.code or str(pack.pk)), error="m").save(qbuf, kind="png", scale=8, border=1)
        qbuf.seek(0)
        qr = Image.open(qbuf).convert("RGB")

        for page_no, page in enumerate(pages, start=1):
            # From here on, coordinates are the standing label's: (0, 0)
            # its bottom-left, PW across, PH up.
            c.saveState()
            c.translate(W, 0)
            c.rotate(90)

            # ── Brand, across the top: who the sack is from ──
            top = PH - M
            if name:
                size = 9
                room = PW - 2 * M
                while size > 6 and brand_width(name, bold, size, LABEL_BRAND_TRACKING) > room:
                    size -= 0.25
                shown = name
                if brand_width(shown, bold, size, LABEL_BRAND_TRACKING) > room:
                    while shown and brand_width(shown + "…", bold, size, LABEL_BRAND_TRACKING) > room:
                        shown = shown[:-1]
                    shown += "…"
                draw_brand(c, M, top - 3.2 * mm, shown, bold, size, LABEL_BRAND_TRACKING)
                top -= BRAND_BAND

            # ── Header: QR, then the order number over "3 / 12"; captions
            #    in Medium, the values bold. ──
            c.drawInlineImage(qr, M, top - qsize, qsize, qsize)
            x = M + qsize + 2.5 * mm
            room = PW - M - x
            c.setFont(caption, 5)
            c.drawString(x, top - 1.8 * mm, _("ORDER").upper())
            package = _("PACKAGE").upper()
            if len(pages) > 1:
                package += f" · {page_no}/{len(pages)}"
            c.drawString(x, top - 9.2 * mm, package)
            # The order number is what people say and search for, so it
            # shrinks to fit rather than lose its tail. The package code
            # isn't printed: it is this number and "3 / 12" over again, and
            # the QR already opens this very package.
            number = combined_number(halves)
            size = shrink(number, bold, 9, room, 5)
            if c.stringWidth(number, bold, size) <= room or len(halves) < 2:
                c.setFont(bold, size)
                c.drawString(x, top - 5.2 * mm, fit(number, bold, size, room))
            else:
                # A split order's two numbers don't fit one line: each
                # half's on a line of its own, "&" after the first, rather
                # than the second losing its tail.
                parts = [half_number(h) for h in halves[:2]]
                parts[0] += " &"
                size = min(shrink(p, bold, 6.5, room, 5) for p in parts)
                c.setFont(bold, size)
                c.drawString(x, top - 4.3 * mm, fit(parts[0], bold, size, room))
                c.drawString(x, top - 6.7 * mm, fit(parts[1], bold, size, room))
            c.setFont(bold, 11)
            c.drawString(x, top - 13 * mm, f"{pack.pack_number} / {of}")

            rule = top - qsize - 1.4 * mm
            c.setLineWidth(0.5)
            c.line(M, rule, PW - M, rule)

            # ── Contents: a product a line, its code left and its amount
            #    right on the same baseline (laid out above) ──
            y = rule - 3.2 * mm
            for n, row in enumerate(page):
                if n:
                    # A dotted line between products, so a long code's
                    # amount on the line under it reads as its own. Leader
                    # dots joining code to amount were tried: the gap is
                    # mostly too short, and they came out one dot or none.
                    c.saveState()
                    c.setLineWidth(0.5)
                    c.setLineCap(1)          # round: each dash a dot
                    c.setDash(0.01, 1.4)
                    c.line(M, y + ROW - 1.1 * mm, PW - M, y + ROW - 1.1 * mm)
                    c.restoreState()
                c.setFont(bold, row["size"])
                if row["single"]:
                    c.drawString(M, y, row["sku"])
                    c.setFont(reg, row["size"])
                    c.drawRightString(PW - M, y, row["amount"])
                    y -= ROW
                else:
                    c.drawString(M, y, fit(row["sku"], bold, row["size"], PW - 2 * M))
                    c.setFont(reg, row["size"])
                    c.drawRightString(PW - M, y - UNDER,
                                      fit(row["amount"], reg, row["size"], PW - 2 * M))
                    y -= ROW + UNDER
            if not lines:
                c.setFont(reg, 7.5)
                c.drawString(M, y, _("Empty"))

            # ── Footer: the whole package's total ──
            c.line(M, 6.4 * mm, PW - M, 6.4 * mm)
            text = f"{_('Total')}: {total}"
            size = shrink(text, bold, 7.5, PW - 2 * M, 6)
            c.setFont(bold, size)
            c.drawString(M, 2.6 * mm, fit(text, bold, size, PW - 2 * M))

            c.restoreState()
            c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def _packing_list_link(request):
    """The QR's target: the order's packing list, scrolled to this package
    and lit up. Behind the sign-in, like the rest of the ERP — a label is
    scanned by staff, not by whoever finds the sack."""
    def link(pack):
        url = reverse("operating:order_packing_list", kwargs={"pk": pack.order_id})
        return request.build_absolute_uri(url) + f"#pack-{pack.pk}"
    return link


def pack_label(request, pack_pk):
    """One package's label(s), inline for the label printer."""
    pack = get_object_or_404(Pack.objects.select_related("order"), pk=pack_pk)
    pdf = labels_pdf_bytes([pack], title=f"{_('Package label')} — {pack.code}",
                           link=_packing_list_link(request), brand=label_brand(request))
    return inline_pdf_response(pdf, f"package-label-{pack.code or pack.pk}")


def order_pack_labels(request, pk):
    """Every package of an order, a label each, to print in one go."""
    order = get_object_or_404(Order, pk=pk)
    packs = list(order_packs(order))
    pdf = labels_pdf_bytes(packs, title=f"{_('Package labels')} — {combined_number(split_halves(order))}",
                           link=_packing_list_link(request), brand=label_brand(request))
    return inline_pdf_response(pdf, f"package-labels-{order.order_number or order.pk}")
