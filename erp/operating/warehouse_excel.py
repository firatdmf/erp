"""Excel (.xlsx) export of a Warehouse's product list — a plain data table
(SKU / Name / Model / Barcode / Stock / Tops / Reserved / Unit cost / Total
value / Last update), honoring the same search + sort as the on-screen list.
"""
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from erp.xlsx_utils import (
    cell, merge, GRID, RULE, FILL_HEAD, FILL_LBL, RIGHT, LEFT,
    F_TITLE, F_SUB, F_DOCNO, F_HEAD, F_VAL, F_VALB,
)

from .models import Warehouse, WarehouseProduct, WarehouseProductRoll
from .views_warehouse import _tr_ci_variants, reserved_meters_subquery

NCOLS = 10  # A..J


def _dec(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _dt(v):
    try:
        return v.strftime("%d.%m.%Y %H:%M") if v else "—"
    except Exception:
        return "—"


def _filtered_products(warehouse, search, sort):
    qs = WarehouseProduct.objects.filter(warehouse=warehouse)
    if search:
        from functools import reduce
        import operator
        variants = _tr_ci_variants(search)

        def _field_q(field):
            return reduce(operator.or_,
                          (Q(**{f"{field}__icontains": v}) for v in variants))

        roll_match = (WarehouseProductRoll.objects
                      .filter(product__warehouse=warehouse)
                      .filter(_field_q("barcode"))
                      .values('product_id'))
        qs = qs.filter(
            _field_q("name") | _field_q("sku") | _field_q("barcode")
            | Q(id__in=roll_match)
        )

    qs = qs.annotate(roll_count=Count('rolls'),
                      line_usd=F('quantity') * F('cost_usd'),
                      line_try=F('quantity') * F('cost_try'),
                      reserved=reserved_meters_subquery())

    _sort_map = {
        "name_asc": "name", "name_desc": "-name",
        "qty_desc": "-quantity", "qty_asc": "quantity",
        "recent": "-updated_at",
    }
    if sort == "price_desc":
        qs = qs.order_by(F("cost_usd").desc(nulls_last=True), "name", "id")
    elif sort == "price_asc":
        qs = qs.order_by(F("cost_usd").asc(nulls_last=True), "name", "id")
    else:
        qs = qs.order_by(_sort_map.get(sort, "name"), "sku", "id")
    return qs


def build_warehouse_workbook(warehouse, search="", sort="name_asc"):
    from openpyxl import Workbook

    brand = (getattr(settings, "BRAND_NAME", "") or "Nejum")
    products = list(_filtered_products(warehouse, search, sort))

    wb = Workbook()
    ws = wb.active
    ws.title = "Depo"
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFGHIJ", (16, 34, 16, 18, 12, 8, 12, 14, 14, 16)):
        ws.column_dimensions[col].width = w

    # ── Header ──
    r = 1
    cell(ws, r, 1, brand.upper(), font=F_TITLE)
    merge(ws, r, 1, 4)
    cell(ws, r, 5, warehouse.name, font=F_DOCNO, align=RIGHT)
    merge(ws, r, 5, NCOLS)
    r += 1
    cell(ws, r, 1, "Depo Ürün Listesi", font=F_SUB)
    merge(ws, r, 1, 4)
    subtitle = f"{len(products)} ürün"
    if search:
        subtitle += f' · "{search}" için filtrelendi'
    cell(ws, r, 5, subtitle, font=F_SUB, align=RIGHT)
    merge(ws, r, 5, NCOLS)
    for c in range(1, NCOLS + 1):
        ws.cell(r, c).border = RULE
    r += 2

    # ── Table header ──
    heads = ["SKU", "Ürün Adı", "Model", "Barkod", "Stok (m)", "Kupon",
             "Rezerve (m)", "Br. Maliyet", "Toplam (USD)", "Toplam (TRY)"]
    for i, h in enumerate(heads, 1):
        cell(ws, r, i, h, font=F_HEAD, fill=FILL_HEAD, border=GRID,
             align=(RIGHT if i >= 5 else LEFT))
    r += 1

    total_qty = total_usd = total_try = 0.0
    for p in products:
        unit_cost = ""
        if p.purchase_price is not None:
            unit_cost = f"{_dec(p.purchase_price):,.2f} {p.purchase_currency}"
        cell(ws, r, 1, p.sku or "—", font=F_VAL, border=GRID)
        cell(ws, r, 2, p.name, font=F_VAL, border=GRID)
        cell(ws, r, 3, p.model or "—", font=F_VAL, border=GRID)
        cell(ws, r, 4, p.barcode or "—", font=F_VAL, border=GRID)
        cell(ws, r, 5, _dec(p.quantity), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00")
        cell(ws, r, 6, p.roll_count or 0, font=F_VAL, border=GRID, align=RIGHT)
        cell(ws, r, 7, _dec(p.reserved), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00")
        cell(ws, r, 8, unit_cost or "—", font=F_VAL, border=GRID, align=RIGHT)
        cell(ws, r, 9, _dec(p.line_usd), font=F_VAL, border=GRID, align=RIGHT, fmt='#,##0.00" USD"')
        cell(ws, r, 10, _dec(p.line_try), font=F_VAL, border=GRID, align=RIGHT, fmt='#,##0.00" TRY"')
        total_qty += _dec(p.quantity)
        total_usd += _dec(p.line_usd)
        total_try += _dec(p.line_try)
        r += 1

    # ── Totals ──
    for c in range(1, NCOLS + 1):
        cell(ws, r, c, "", font=F_VALB, border=GRID, fill=FILL_LBL)
    cell(ws, r, 4, "TOPLAM", font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT)
    cell(ws, r, 5, total_qty, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt="#,##0.00")
    cell(ws, r, 9, total_usd, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt='#,##0.00" USD"')
    cell(ws, r, 10, total_try, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt='#,##0.00" TRY"')

    return wb


@login_required
def warehouse_excel(request, pk):
    """Download this warehouse's product list as an .xlsx file, honoring the
    same ?search= / ?sort= the on-screen list is currently filtered by."""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    search = (request.GET.get('search') or '').strip()
    sort = (request.GET.get('sort') or 'name_asc').strip()
    wb = build_warehouse_workbook(warehouse, search=search, sort=sort)
    buf = BytesIO()
    wb.save(buf)
    label = f"depo-{warehouse.pk}-{warehouse.name}".replace("/", "-")
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{label}.xlsx"'
    return resp
