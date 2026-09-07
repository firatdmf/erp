"""Excel (.xlsx) export of a Warehouse's product list — a plain data table
(SKU / Name / Model / Barcode / [Location] / Stock / Stock items / Reserved /
Unit cost / Total value), honoring the same search + sort as the on-screen
list.

A combined (ortak) warehouse exports its members' stock, so it grows a
Location column naming the member each row stands on — the same column the
page shows.
"""
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from erp.xlsx_utils import (
    cell, merge, GRID, RULE, FILL_HEAD, FILL_LBL, RIGHT, LEFT,
    F_TITLE, F_SUB, F_DOCNO, F_HEAD, F_VAL, F_VALB,
)

from .models import Warehouse, WarehouseProduct
from .views_warehouse import (reserved_meters_subquery,
                              warehouse_search_mode, warehouse_search_q)

NCOLS = 9  # A..I — plus a Location column on a combined (ortak) warehouse


def _dec(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _cost_currency(warehouse):
    """Code of the currency this warehouse's stock is costed in — the base
    currency of the book that owns it, which is what unit_cost_base holds.
    A combined (ortak) export can list rows from members in different books,
    so it is read per row rather than once for the sheet."""
    book = getattr(warehouse, "accounting_book", None)
    currency = getattr(book, "base_currency", None)
    return getattr(currency, "code", "") or ""


def _dt(v):
    try:
        return v.strftime("%d.%m.%Y %H:%M") if v else "—"
    except Exception:
        return "—"


def _filtered_products(warehouse, search, sort, search_by="text"):
    # Combined (ortak) warehouses export their MEMBERS' stock.
    scope_ids = warehouse.scope_ids()
    qs = WarehouseProduct.objects.filter(warehouse_id__in=scope_ids)
    if search:
        # Same filter the page's search box builds, so the export holds
        # exactly the rows that were on screen.
        qs = qs.filter(warehouse_search_q(search, scope_ids, search_by))

    # Line value comes from the SAME place the warehouse page and the
    # balance sheet get it: the stock on the floor, each item at cost
    # (WarehouseProduct.with_stock_costs). The export used to multiply
    # quantity by the SKU's unit cost, which is a last-purchase price, so
    # a dearer delivery restated every metre already on the shelf and the
    # TOPLAM moved without a metre going anywhere.
    qs = (WarehouseProduct.with_stock_costs(qs)
          .select_related("warehouse__accounting_book__base_currency"))
    _money = DecimalField(max_digits=20, decimal_places=4)
    # Count LIVE stock items only — the warehouse list page counts the same way
    # (~Q(stock_items__status='consumed')), so counting all of them here made the
    # export disagree with the screen it was exported from.
    qs = qs.annotate(roll_count=Count('stock_items',
                                      filter=~Q(stock_items__status='consumed')),
                      line_usd=ExpressionWrapper(F('stock_value'),
                                                 output_field=_money),
                      reserved=reserved_meters_subquery())

    _sort_map = {
        "name_asc": "name", "name_desc": "-name",
        "qty_desc": "-quantity", "qty_asc": "quantity",
        "recent": "-updated_at",
    }
    if sort == "price_desc":
        qs = qs.order_by(F("avg_cost").desc(nulls_last=True), "name", "id")
    elif sort == "price_asc":
        qs = qs.order_by(F("avg_cost").asc(nulls_last=True), "name", "id")
    else:
        qs = qs.order_by(_sort_map.get(sort, "name"), "sku", "id")
    return qs


def build_warehouse_workbook(warehouse, search="", sort="name_asc",
                             search_by="text"):
    from openpyxl import Workbook

    brand = (getattr(settings, "BRAND_NAME", "") or "Nejum")
    products = list(_filtered_products(warehouse, search, sort, search_by))

    # A combined (ortak) warehouse pools several members' shelves, so a row
    # is ambiguous without saying which one it came off.
    show_location = warehouse.is_combined
    ncols = NCOLS + (1 if show_location else 0)

    wb = Workbook()
    ws = wb.active
    ws.title = "Depo"
    ws.sheet_view.showGridLines = False
    widths = [16, 34, 16, 18, 12, 8, 12, 14, 14]
    if show_location:
        widths.insert(4, 20)
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(ord("A") + i)].width = w

    # ── Header ──
    r = 1
    cell(ws, r, 1, brand.upper(), font=F_TITLE)
    merge(ws, r, 1, 4)
    cell(ws, r, 5, warehouse.name, font=F_DOCNO, align=RIGHT)
    merge(ws, r, 5, ncols)
    r += 1
    cell(ws, r, 1, "Depo Ürün Listesi", font=F_SUB)
    merge(ws, r, 1, 4)
    subtitle = f"{len(products)} ürün"
    if search:
        subtitle += f' · "{search}" için filtrelendi'
    cell(ws, r, 5, subtitle, font=F_SUB, align=RIGHT)
    merge(ws, r, 5, ncols)
    for c in range(1, ncols + 1):
        ws.cell(r, c).border = RULE
    r += 2

    # ── Table header ──
    heads = ["SKU", "Ürün Adı", "Model", "Barkod", "Stok (m)", "Kupon",
             "Rezerve (m)", "Br. Maliyet", "Toplam (USD)"]
    if show_location:
        heads.insert(4, "Depo")
    # Location is text like the four columns before it; the numeric block
    # (stock onward) stays right-aligned, so the boundary moves with it.
    first_num = 6 if show_location else 5
    for i, h in enumerate(heads, 1):
        cell(ws, r, i, h, font=F_HEAD, fill=FILL_HEAD, border=GRID,
             align=(RIGHT if i >= first_num else LEFT))
    r += 1

    total_qty = total_usd = 0.0
    for p in products:
        # The WEIGHTED AVERAGE cost of the stock on the floor — the same
        # number the screen shows, and the one Toplam is built from. This
        # column used to print purchase_price, a last-purchase price, so
        # Br. Maliyet x Stok never came to Toplam.
        unit_cost = ""
        if p.avg_cost is not None:
            unit_cost = f"{_dec(p.avg_cost):,.4f} {_cost_currency(p.warehouse)}".strip()
        c = 1
        cell(ws, r, c, p.sku or "—", font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, p.name, font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, p.model or "—", font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, p.barcode or "—", font=F_VAL, border=GRID); c += 1
        if show_location:
            cell(ws, r, c, p.warehouse.name, font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, _dec(p.quantity), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00"); c += 1
        cell(ws, r, c, p.roll_count or 0, font=F_VAL, border=GRID, align=RIGHT); c += 1
        cell(ws, r, c, _dec(p.reserved), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00"); c += 1
        cell(ws, r, c, unit_cost or "—", font=F_VAL, border=GRID, align=RIGHT); c += 1
        cell(ws, r, c, _dec(p.line_usd), font=F_VAL, border=GRID, align=RIGHT, fmt='#,##0.00" USD"')
        total_qty += _dec(p.quantity)
        total_usd += _dec(p.line_usd)
        r += 1

    # ── Totals ──
    for c in range(1, ncols + 1):
        cell(ws, r, c, "", font=F_VALB, border=GRID, fill=FILL_LBL)
    cell(ws, r, first_num - 1, "TOPLAM", font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT)
    cell(ws, r, first_num, total_qty, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt="#,##0.00")
    cell(ws, r, ncols, total_usd, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt='#,##0.00" USD"')

    return wb


@login_required
def warehouse_excel(request, pk):
    """Download this warehouse's product list as an .xlsx file, honoring the
    same ?search= / ?search_by= / ?sort= the on-screen list is currently
    filtered by."""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    search = (request.GET.get('search') or '').strip()
    sort = (request.GET.get('sort') or 'name_asc').strip()
    wb = build_warehouse_workbook(warehouse, search=search, sort=sort,
                                  search_by=warehouse_search_mode(request))
    buf = BytesIO()
    wb.save(buf)
    label = f"depo-{warehouse.pk}-{warehouse.name}".replace("/", "-")
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{label}.xlsx"'
    return resp
