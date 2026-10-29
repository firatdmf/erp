"""Mini packing list for the outside of a package: 100 × 100 mm, one label
per page, for the thermal label printer.

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
from .split_orders import combined_number, order_packs, split_halves
from .warehouse_label import inline_pdf_response, label_brand

LINES_PER_LABEL = 9


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

    from .order_notifications import _ensure_pdf_fonts

    reg = _ensure_pdf_fonts() or "Helvetica"
    bold = "DejaVuSans-Bold" if reg == "DejaVuSans" else "Helvetica-Bold"

    W, H, M = 100 * mm, 100 * mm, 5 * mm
    qsize = 24 * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(title)

    def fit(text, font, size, width):
        if c.stringWidth(text, font, size) <= width:
            return text
        while text and c.stringWidth(text + "…", font, size) > width:
            text = text[:-1]
        return text + "…"

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
        pages = [lines[i:i + LINES_PER_LABEL]
                 for i in range(0, len(lines), LINES_PER_LABEL)] or [[]]

        qbuf = BytesIO()
        segno.make(link(pack) if link else (pack.code or str(pack.pk)), error="m").save(qbuf, kind="png", scale=8, border=1)
        qbuf.seek(0)
        qr = Image.open(qbuf).convert("RGB")

        for page_no, page in enumerate(pages, start=1):
            # ── Brand, across the top: who the sack is from ──
            top = H - M
            if name:
                size = 14
                while size > 8 and c.stringWidth(name, bold, size) > W - 2 * M:
                    size -= 0.5
                c.setFont(bold, size)
                c.drawString(M, H - M - 4.5 * mm, fit(name, bold, size, W - 2 * M))
                top -= 8 * mm

            # ── Header: QR, then the order number over "3 / 12" ──
            c.drawInlineImage(qr, M, top - qsize, qsize, qsize)
            x = M + qsize + 4 * mm
            c.setFont(reg, 8)
            c.drawString(x, top - 3 * mm, _("ORDER").upper())
            package = _("PACKAGE").upper()
            if len(pages) > 1:
                package += f" · {page_no}/{len(pages)}"
            c.drawString(x, top - 15 * mm, package)
            # The order number is what people say and search for, so it
            # shrinks to fit rather than lose its tail. The package code
            # isn't printed: it is this number and "3 / 12" over again, and
            # the QR already opens this very package.
            number = combined_number(halves)
            size = 20
            while size > 10 and c.stringWidth(number, bold, size) > W - M - x:
                size -= 0.5
            c.setFont(bold, size)
            c.drawString(x, top - 10 * mm, fit(number, bold, size, W - M - x))
            c.setFont(bold, 20)
            c.drawString(x, top - 22 * mm, f"{pack.pack_number} / {of}")

            rule = top - qsize - 2.5 * mm
            c.setLineWidth(0.6)
            c.line(M, rule, W - M, rule)

            # ── Contents, one line per SKU ──
            y = rule - 6 * mm
            for line in page:
                amount = _describe(line["items"], line["quantity"], line["unit"], line["pack_type"],
                                   line["tracking"])
                c.setFont(reg, 10)
                c.drawRightString(W - M, y, amount)
                sku_w = W - 2 * M - c.stringWidth(amount, reg, 10) - 3 * mm
                c.setFont(bold, 10)
                c.drawString(M, y, fit(line["sku"], bold, 10, sku_w))
                y -= 4.8 * mm
            if not lines:
                c.setFont(reg, 10)
                c.drawString(M, y, _("Empty"))

            # ── Footer: the whole package's total ──
            c.line(M, 14 * mm, W - M, 14 * mm)
            c.setFont(bold, 11)
            c.drawString(M, 8 * mm, fit(f"{_('Total')}: {total}", bold, 11, W - 2 * M))

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
