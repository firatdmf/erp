"""Excel (.xlsx) export of a Warehouse's product list — a plain data table
(SKU / Name / Model / Barcode / [Location] / Stock / Stock items / Reserved /
Unit cost / Total value), honoring the same search + sort as the on-screen
list.

A combined (ortak) warehouse exports its members' stock, so it grows a
Location column naming the member each row stands on — the same column the
page shows.

A sales rep does not read cost: their export prices each row at the sales
price derived from the unit cost and leaves out the total
column and grand total, which are cost times quantity.
"""
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _gettext, ngettext, pgettext

from erp.roles import is_sales_rep, sales_rep_price
from erp.xlsx_utils import (
    cell, merge, GRID, RULE, FILL_HEAD, FILL_LBL, RIGHT, LEFT, TEXT,
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


def _filtered_products(warehouse, search, sort, search_by="text",
                       show_empty=False, reserved_only=False):
    # Combined (ortak) warehouses export their MEMBERS' stock.
    scope_ids = warehouse.scope_ids()
    qs = WarehouseProduct.objects.filter(warehouse_id__in=scope_ids)
    # The page's filters, applied the way WarehouseDetail applies them, so
    # the export holds exactly the rows that were on screen: no empty rows
    # unless "show empty" was ticked.
    if not show_empty:
        qs = qs.exclude(quantity=0)
    if search:
        qs = qs.filter(warehouse_search_q(search, scope_ids, search_by))
    if reserved_only:
        from .models import OrderStockReservation
        qs = qs.filter(id__in=(OrderStockReservation.objects
                               .filter(consumed=False)
                               .values("warehouse_product_id")))

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
    # A sold-out SKU sorts by its last cost, as on the page.
    if sort in ("price_desc", "price_asc"):
        qs = qs.annotate(_price=Coalesce("avg_cost", "last_cost"))
    if sort == "price_desc":
        qs = qs.order_by(F("_price").desc(nulls_last=True), "name", "id")
    elif sort == "price_asc":
        qs = qs.order_by(F("_price").asc(nulls_last=True), "name", "id")
    else:
        qs = qs.order_by(_sort_map.get(sort, "name"), "sku", "id")
    return qs


def build_warehouse_workbook(warehouse, search="", sort="name_asc",
                             search_by="text", for_sales_rep=False,
                             show_empty=False, reserved_only=False):
    from openpyxl import Workbook

    from erp.branding import brand as brand_value
    brand = brand_value("BRAND_NAME") or "Nejum"
    products = list(_filtered_products(warehouse, search, sort, search_by,
                                       show_empty, reserved_only))

    # A combined (ortak) warehouse pools several members' shelves, so a row
    # is ambiguous without saying which one it came off.
    show_location = warehouse.is_combined
    # A sales rep's sheet has no total column — see the module docstring.
    show_total = not for_sales_rep
    ncols = NCOLS + (1 if show_location else 0) - (0 if show_total else 1)

    wb = Workbook()
    ws = wb.active
    ws.title = pgettext("warehouse sheet", "Warehouse")
    ws.sheet_view.showGridLines = False
    widths = [16, 34, 16, 18, 12, 8, 12, 14, 14]
    if not show_total:
        widths.pop()
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
    cell(ws, r, 1, _gettext("Warehouse product list"), font=F_SUB)
    merge(ws, r, 1, 4)
    subtitle = ngettext("%(count)s product", "%(count)s products",
                        len(products)) % {"count": len(products)}
    if search:
        subtitle += " · " + _gettext('filtered for "%(search)s"') % {"search": search}
    # The page's other filters, so a sheet opened later says it is not the
    # whole warehouse.
    if reserved_only:
        subtitle += " · " + pgettext("warehouse sheet", "reserved only")
    if show_empty:
        subtitle += " · " + pgettext("warehouse sheet", "including empty")
    cell(ws, r, 5, subtitle, font=F_SUB, align=RIGHT)
    merge(ws, r, 5, ncols)
    for c in range(1, ncols + 1):
        ws.cell(r, c).border = RULE
    r += 2

    # ── Table header ──
    X = "warehouse sheet"
    heads = ["SKU", pgettext(X, "Product name"), pgettext(X, "Model"), pgettext(X, "Barcode"),
             pgettext(X, "Stock (m)"), pgettext(X, "Rolls"), pgettext(X, "Reserved (m)"),
             pgettext(X, "Unit cost"), pgettext(X, "Total (USD)")]
    if not show_total:
        heads[-2:] = [pgettext(X, "Unit price")]
    if show_location:
        heads.insert(4, pgettext(X, "Warehouse"))
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
        # number the screen shows, and the one the total is built from. This
        # column used to print purchase_price, a last-purchase price, so
        # unit cost x stock never came to the total.
        # With nothing on the floor there is no average; the page then
        # shows the last cost received, and so does the sheet, marked so it
        # is not read as the cost of stock on hand.
        cost = p.avg_cost if p.avg_cost is not None else p.last_cost
        unit_cost = ""
        if cost is not None and for_sales_rep:
            # The price derived from the cost, which moves in 0.05 steps —
            # two decimals say all of it.
            unit_cost = (f"{_dec(sales_rep_price(cost)):,.2f} "
                         f"{_cost_currency(p.warehouse)}").strip()
        elif cost is not None:
            unit_cost = f"{_dec(cost):,.4f} {_cost_currency(p.warehouse)}".strip()
        if unit_cost and p.avg_cost is None:
            unit_cost += " (" + pgettext("warehouse sheet", "last cost") + ")"
        c = 1
        cell(ws, r, c, p.sku or "—", font=F_VAL, border=GRID, fmt=TEXT); c += 1
        cell(ws, r, c, p.name, font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, p.model or "—", font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, p.barcode or "—", font=F_VAL, border=GRID, fmt=TEXT); c += 1
        if show_location:
            cell(ws, r, c, p.warehouse.name, font=F_VAL, border=GRID); c += 1
        cell(ws, r, c, _dec(p.quantity), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00"); c += 1
        cell(ws, r, c, p.roll_count or 0, font=F_VAL, border=GRID, align=RIGHT); c += 1
        cell(ws, r, c, _dec(p.reserved), font=F_VAL, border=GRID, align=RIGHT, fmt="#,##0.00"); c += 1
        cell(ws, r, c, unit_cost or "—", font=F_VAL, border=GRID, align=RIGHT); c += 1
        if show_total:
            cell(ws, r, c, _dec(p.line_usd), font=F_VAL, border=GRID, align=RIGHT, fmt='#,##0.00" USD"')
            total_usd += _dec(p.line_usd)
        total_qty += _dec(p.quantity)
        r += 1

    # ── Totals ──
    for c in range(1, ncols + 1):
        cell(ws, r, c, "", font=F_VALB, border=GRID, fill=FILL_LBL)
    cell(ws, r, first_num - 1, pgettext(X, "TOTAL"), font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT)
    cell(ws, r, first_num, total_qty, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt="#,##0.00")
    if show_total:
        cell(ws, r, ncols, total_usd, font=F_VALB, border=GRID, fill=FILL_LBL, align=RIGHT, fmt='#,##0.00" USD"')

    return wb


@login_required
def warehouse_excel(request, pk):
    """Download this warehouse's product list as an .xlsx file, honoring the
    same ?search= / ?search_by= / ?sort= / ?show_empty= / ?reserved_only=
    the on-screen list is currently filtered by."""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    search = (request.GET.get('search') or '').strip()
    sort = (request.GET.get('sort') or 'name_asc').strip()
    on = ('1', 'true', 'on')
    wb = build_warehouse_workbook(
        warehouse, search=search, sort=sort,
        search_by=warehouse_search_mode(request),
        for_sales_rep=is_sales_rep(request.user),
        show_empty=(request.GET.get('show_empty') or '').strip() in on,
        reserved_only=(request.GET.get('reserved_only') or '').strip() in on)
    buf = BytesIO()
    wb.save(buf)
    label = f"depo-{warehouse.pk}-{warehouse.name}".replace("/", "-")
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{label}.xlsx"'
    return resp
