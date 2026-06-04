"""Excel (.xlsx) export of an Order — bordered, document-style sheet that
mirrors the printable order PDF and carries the full order record.
"""
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from erp.xlsx_utils import (
    cell, merge, merge_border, section, kv_full, kv_pair,
    GRID, RULE, FILL_HEAD, RIGHT, LEFT, TOP,
    F_TITLE, F_SUB, F_DOCNO, F_HEAD, F_VAL, F_VALB, F_TOTAL,
)
from .models import Order

NCOLS = 6  # A..F


def _dec(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _dt(v, fmt="%d %b %Y · %H:%M"):
    try:
        return v.strftime(fmt) if v else "—"
    except Exception:
        return "—"


def _firstv(v):
    if isinstance(v, (list, tuple)):
        return (v[0] if v else "") or ""
    return v or ""


def build_order_workbook(order):
    from openpyxl import Workbook

    brand = (getattr(settings, "BRAND_NAME", "") or "Nejum")
    ccode = (order.original_currency or order.paid_currency or "USD")
    money = f'#,##0.00" {ccode}"'

    wb = Workbook()
    ws = wb.active
    ws.title = "Order"
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEF", (32, 22, 18, 11, 15, 16)):
        ws.column_dimensions[col].width = w

    num = order.order_number or f"#{order.pk}"

    # ── Header ──
    r = 1
    cell(ws, r, 1, brand.upper(), font=F_TITLE)
    merge(ws, r, 1, 3)
    cell(ws, r, 4, f"ORDER {num}", font=F_DOCNO, align=RIGHT)
    merge(ws, r, 4, 6)
    r += 1
    cell(ws, r, 1, "Order Confirmation", font=F_SUB)
    merge(ws, r, 1, 3)
    cell(ws, r, 4, _dt(order.created_at), font=F_SUB, align=RIGHT)
    merge(ws, r, 4, 6)
    for c in range(1, NCOLS + 1):
        ws.cell(r, c).border = RULE
    r += 2

    # ── Order details ──
    r = section(ws, r, "ORDER DETAILS", NCOLS)
    payment = ""
    if getattr(order, "payment_status", None):
        try:
            payment = order.get_payment_status_display()
        except Exception:
            payment = order.payment_status
    r = kv_pair(ws, r, "Order No", num, "Status", order.get_status_display() or order.status, NCOLS)
    r = kv_pair(ws, r, "Order Date", _dt(order.created_at), "Payment", payment or "—", NCOLS)
    cari_name = order.cari.name if (order.cari_id and order.cari) else "—"
    r = kv_pair(ws, r, "Last Update", _dt(order.updated_at), "Currency", ccode, NCOLS)
    r = kv_full(ws, r, "Linked Account", cari_name, NCOLS)
    r += 1

    # ── Customer ──
    r = section(ws, r, "CUSTOMER", NCOLS)
    if order.contact_id and order.contact:
        ct = order.contact
        r = kv_full(ws, r, "Type", "Contact", NCOLS)
        r = kv_full(ws, r, "Name", ct.name or "—", NCOLS, bold_value=True)
        r = kv_full(ws, r, "Email", _firstv(ct.email), NCOLS)
        r = kv_full(ws, r, "Phone", _firstv(ct.phone), NCOLS)
        if getattr(ct, "address", ""):
            r = kv_full(ws, r, "Address", ct.address, NCOLS)
        if getattr(ct, "company", ""):
            r = kv_full(ws, r, "Company", ct.company, NCOLS)
    elif order.company_id and order.company:
        co = order.company
        r = kv_full(ws, r, "Type", "Company", NCOLS)
        r = kv_full(ws, r, "Name", co.name or "—", NCOLS, bold_value=True)
        r = kv_full(ws, r, "Email", _firstv(getattr(co, "email", "")), NCOLS)
        r = kv_full(ws, r, "Phone", _firstv(getattr(co, "phone", "")), NCOLS)
        if getattr(co, "address", ""):
            r = kv_full(ws, r, "Address", co.address, NCOLS)
        if getattr(co, "tax_office", ""):
            r = kv_full(ws, r, "Tax Office", co.tax_office, NCOLS)
        if getattr(co, "tax_number", ""):
            r = kv_full(ws, r, "Tax No", co.tax_number, NCOLS)
    elif order.web_client_id and order.web_client:
        wc = order.web_client
        r = kv_full(ws, r, "Type", "Web Customer", NCOLS)
        r = kv_full(ws, r, "Name", getattr(wc, "name", "") or getattr(wc, "username", "") or "—", NCOLS, bold_value=True)
        r = kv_full(ws, r, "Email", getattr(wc, "email", ""), NCOLS)
        r = kv_full(ws, r, "Phone", getattr(wc, "phone", ""), NCOLS)
    elif getattr(order, "is_guest_order", False):
        r = kv_full(ws, r, "Type", "Guest", NCOLS)
        gname = " ".join(p for p in [order.guest_first_name or "", order.guest_last_name or ""] if p)
        r = kv_full(ws, r, "Name", gname or "—", NCOLS, bold_value=True)
        r = kv_full(ws, r, "Email", order.guest_email or "", NCOLS)
        r = kv_full(ws, r, "Phone", order.guest_phone or "", NCOLS)
    else:
        r = kv_full(ws, r, "Name", "—", NCOLS, bold_value=True)
    r += 1

    # ── Delivery address ──
    r = section(ws, r, "DELIVERY ADDRESS", NCOLS)
    if order.delivery_address or order.delivery_city:
        if order.delivery_address_title:
            r = kv_full(ws, r, "Title", order.delivery_address_title, NCOLS)
        if order.delivery_address:
            r = kv_full(ws, r, "Address", order.delivery_address, NCOLS)
        loc = ", ".join([x for x in [order.delivery_city, order.delivery_country] if x])
        if loc:
            r = kv_full(ws, r, "City / Country", loc, NCOLS)
        if order.delivery_phone:
            r = kv_full(ws, r, "Phone", order.delivery_phone, NCOLS)
    else:
        r = kv_full(ws, r, "Address", "Same as customer", NCOLS)
    r += 1

    # ── Billing address (only if set) ──
    if order.billing_address or order.billing_city:
        r = section(ws, r, "BILLING ADDRESS", NCOLS)
        if order.billing_address_title:
            r = kv_full(ws, r, "Title", order.billing_address_title, NCOLS)
        if order.billing_address:
            r = kv_full(ws, r, "Address", order.billing_address, NCOLS)
        loc = ", ".join([x for x in [order.billing_city, order.billing_country] if x])
        if loc:
            r = kv_full(ws, r, "City / Country", loc, NCOLS)
        if order.billing_phone:
            r = kv_full(ws, r, "Phone", order.billing_phone, NCOLS)
        r += 1

    # ── Items ──
    items = list(order.items.all().select_related("product", "product_variant"))
    r = section(ws, r, f"PRODUCTS ({len(items)})", NCOLS)
    heads = ["Product", "SKU", "Variant", "Qty", "Unit", "Amount"]
    for i, h in enumerate(heads, 1):
        cell(ws, r, i, h, font=F_HEAD, fill=FILL_HEAD, border=GRID,
             align=(RIGHT if i >= 4 else LEFT))
    r += 1

    total = Decimal("0.00")
    for it in items:
        qty = it.quantity or Decimal("0")
        price = it.price or Decimal("0")
        line = (qty * price).quantize(Decimal("0.01"))
        total += line
        title = getattr(it.product, "title", None) or str(it.product or "—")
        if getattr(it, "description", ""):
            title = f"{title}\n{it.description}"
        vsku = it.product_variant.variant_sku if (it.product_variant_id and it.product_variant) else "—"
        cell(ws, r, 1, title, font=F_VAL, border=GRID, align=TOP)
        cell(ws, r, 2, getattr(it.product, "sku", "") or "—", font=F_VAL, border=GRID)
        cell(ws, r, 3, vsku or "—", font=F_VAL, border=GRID)
        cell(ws, r, 4, _dec(qty), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00")
        cell(ws, r, 5, _dec(price), font=F_VAL, border=GRID, align=RIGHT, fmt=money)
        cell(ws, r, 6, _dec(line), font=F_VAL, border=GRID, align=RIGHT, fmt=money)
        r += 1

    # ── Totals ──
    paid = _dec(getattr(order, "paid_amount", 0))
    grand = _dec(total)
    rows = [("Total", grand, True)]
    if paid:
        rows += [("Paid", paid, False), ("Balance", grand - paid, True)]
    for lbl, val, strong in rows:
        cell(ws, r, 4, lbl, font=(F_TOTAL if strong else F_VALB), border=GRID, align=RIGHT)
        merge(ws, r, 4, 5)
        merge_border(ws, r, 4, 5, GRID)
        cell(ws, r, 6, val, font=(F_TOTAL if strong else F_VALB), border=GRID, align=RIGHT, fmt=money)
        r += 1

    # ── Notes ──
    if order.notes:
        r += 1
        r = section(ws, r, "NOTES", NCOLS)
        cell(ws, r, 1, order.notes, font=F_VAL, border=GRID, align=TOP)
        merge(ws, r, 1, NCOLS)
        merge_border(ws, r, 1, NCOLS, GRID)
        ws.row_dimensions[r].height = 46

    return wb


@login_required
def order_excel(request, pk):
    """Download the order as an .xlsx file."""
    order = get_object_or_404(Order, pk=pk)
    wb = build_order_workbook(order)
    buf = BytesIO()
    wb.save(buf)
    label = order.order_number or f"order-{order.pk}"
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{label}.xlsx"'
    return resp
