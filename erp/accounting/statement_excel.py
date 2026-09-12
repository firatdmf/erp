"""Excel (.xlsx) export of a combined current-account statement.

The same document CurrentAccountStatementPrintCombined renders, in the
format people actually reconcile in. The two are one sheet in two
formats, so they share both the selection guard
(select_combined_accounts) and the merge itself (combined_statement) —
a rule or a total that lived in only one of them would be a second
answer waiting to disagree with the first.

Like the printable sheet, it carries an Account column and names each
account's book beside its code in the header — asked for so a reader can
tell at a glance which of the two ledgers a line came from.
"""
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from erp.xlsx_utils import (
    cell, merge, merge_border, kv_full,
    GRID, FILL_HEAD, RIGHT, LEFT,
    F_TITLE, F_SUB, F_HEAD, F_VAL, F_VALB, F_TOTAL,
)

# Date, Account, Type, Description, Reference, Debit, Credit, Balance —
# the same eight the printed sheet carries, in the same order. The two
# are one document in two formats; a column in only one of them would be
# a second answer waiting to disagree with the first.
NCOLS = 8
_HEADERS = ("Date", "Account", "Type", "Description", "Reference",
            "Debit", "Credit", "Balance")
_FIRST_NUM_COL = 6


def _dec(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def build_statement_workbook(accounts, data, *, customer_name, brand_name):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = _("Statement")[:31]
    for col, width in zip("ABCDEFGH", (13, 14, 20, 42, 18, 15, 15, 16)):
        ws.column_dimensions[col].width = width

    sym = data["currency_symbol"]
    money = f'#,##0.00" {sym}"'

    r = 1
    cell(ws, r, 1, brand_name, font=F_TITLE)
    merge(ws, r, 1, NCOLS)
    r += 1
    cell(ws, r, 1, _("Current account statement"), font=F_SUB)
    merge(ws, r, 1, NCOLS)
    r += 2

    r = kv_full(ws, r, _("Customer"), customer_name, NCOLS, bold_value=True)
    # Each code with the book it belongs to, matching the printed sheet.
    r = kv_full(ws, r, _("Account codes"),
                ", ".join(f"{a.code} ({a.book.name})" for a in accounts), NCOLS)
    r = kv_full(ws, r, _("Printed"),
                timezone.now().strftime("%d %b %Y %H:%M"), NCOLS)
    r += 1

    for c, head in enumerate(_HEADERS, start=1):
        cell(ws, r, c, _(head), font=F_HEAD, fill=FILL_HEAD,
             align=RIGHT if c >= _FIRST_NUM_COL else LEFT, border=GRID)
    r += 1

    for row in data["rows"]:
        mv = row["mv"]
        debit = mv.amount_base if mv.amount_base > 0 else None
        credit = -mv.amount_base if mv.amount_base < 0 else None
        cell(ws, r, 1, mv.date.strftime("%d.%m.%Y") if mv.date else "—",
             font=F_VAL, border=GRID)
        cell(ws, r, 2, mv.current_account.code, font=F_VAL, border=GRID)
        cell(ws, r, 3, mv.get_movement_type_display(), font=F_VAL, border=GRID)
        cell(ws, r, 4, row.get("description") or mv.description or "",
             font=F_VAL, border=GRID)
        cell(ws, r, 5, mv.reference or "", font=F_VAL, border=GRID)
        cell(ws, r, 6, _dec(debit) if debit is not None else "",
             font=F_VAL, align=RIGHT, border=GRID, fmt=money)
        cell(ws, r, 7, _dec(credit) if credit is not None else "",
             font=F_VAL, align=RIGHT, border=GRID, fmt=money)
        cell(ws, r, 8, _dec(row["balance_after"]),
             font=F_VALB, align=RIGHT, border=GRID, fmt=money)
        r += 1

    cell(ws, r, 1, _("Total"), font=F_TOTAL, border=GRID)
    merge(ws, r, 1, 5)
    merge_border(ws, r, 1, 5, GRID)
    cell(ws, r, 6, _dec(data["debit_total"]), font=F_TOTAL, align=RIGHT,
         border=GRID, fmt=money)
    cell(ws, r, 7, _dec(data["credit_total"]), font=F_TOTAL, align=RIGHT,
         border=GRID, fmt=money)
    cell(ws, r, 8, _dec(data["closing"]), font=F_TOTAL, align=RIGHT,
         border=GRID, fmt=money)
    r += 2

    # The one figure the customer rang up about.
    closing = data["closing"]
    label = _("Balance owed to us") if closing > 0 else (
        _("Balance we owe") if closing < 0 else _("Account closed"))
    r = kv_full(ws, r, label, f"{abs(closing):,.2f} {sym}", NCOLS,
                bold_value=True)
    return wb


@login_required
def combined_statement_excel(request):
    """Download several of one customer's accounts as one .xlsx."""
    from .views_accounts import select_combined_accounts, _attach_links
    from .services_accounts import brand_name_for, combined_statement

    accounts, refusal = select_combined_accounts(request)
    if refusal is not None:
        return refusal

    data = combined_statement(accounts)
    _attach_links(data["rows"])

    primary = accounts[0]
    who = primary.crm_link
    customer_name = (getattr(who, "name", None)
                     or getattr(who, "company_name", None)
                     or primary.name)

    wb = build_statement_workbook(
        accounts, data, customer_name=customer_name,
        brand_name=brand_name_for())
    buf = BytesIO()
    wb.save(buf)

    label = "".join(ch if ch.isalnum() or ch in " -_" else "-"
                    for ch in customer_name).strip()
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{label or "statement"}.xlsx"'
    return resp
