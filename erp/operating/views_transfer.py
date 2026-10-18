"""Transferring stock from one book's warehouse to another's.

The pages over accounting.services_stock_transfer: one to gather the rolls
and send them, one to read a transfer back and undo it.

A transfer changes two books at once, so it is for someone who works in
both — and not for a sales rep, who is not shown what stock costs.
"""
import json
from datetime import date as _date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View

from accounting.models_transfer import StockTransfer
from accounting.services_accounts import member_books, member_can_use_book
from accounting.services_posting import stock_unit_cost
from accounting.services_stock_transfer import (
    TransferError, receiving_account, roll_problem, transfer_stock, undo_stock_transfer,
)

from .models import Warehouse, WarehouseProduct, WarehouseProductItem


def _member(request):
    return getattr(request.user, "member", None)


def _may_transfer(request, *books):
    from erp.roles import is_sales_rep

    member = _member(request)
    return (not is_sales_rep(request.user)
            and all(member_can_use_book(member, book) for book in books))


def _source_warehouse(request, pk):
    """The warehouse stock is leaving, or 404: it must be a real one, in a
    book this member works in."""
    warehouse = get_object_or_404(Warehouse.objects.select_related("accounting_book"), pk=pk)
    if warehouse.is_combined or not _may_transfer(request, warehouse.accounting_book):
        raise Http404("No such record.")
    return warehouse


def _targets(request, warehouse):
    """Where this warehouse's stock may go: another book's warehouse the
    member also works in, when the two books keep a paired account."""
    books = member_books(_member(request)).exclude(pk=warehouse.accounting_book_id)
    paired = [book for book in books
              if receiving_account(warehouse.accounting_book, book) is not None]
    return list(Warehouse.objects.filter(accounting_book__in=paired, kind="normal")
                .select_related("accounting_book")
                .order_by("accounting_book__name", "name")) if paired else []


def _roll_row(roll):
    left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
    left = Decimal(left or 0)
    cost = stock_unit_cost(roll)
    problem = roll_problem(roll)
    return {
        "id": roll.pk,
        "barcode": roll.barcode or "",
        "sku": roll.product.sku or "",
        "name": roll.product.name or "",
        "quantity": float(left),
        "unit": roll.product.unit_short,
        "unit_cost": float(cost) if cost is not None else None,
        "value": float(left * cost) if cost is not None else None,
        "problem": str(problem) if problem else "",
    }


@method_decorator(login_required, name="dispatch")
class StockTransferCreate(View):
    template_name = "operating/stock_transfer_form.html"

    def get(self, request, pk):
        warehouse = _source_warehouse(request, pk)
        transfers = (StockTransfer.objects
                     .filter(Q(from_warehouse=warehouse) | Q(to_warehouse=warehouse))
                     .select_related("from_warehouse", "to_warehouse", "purchase")
                     .order_by("-date", "-pk")[:20])
        return render(request, self.template_name, {
            "warehouse": warehouse,
            "targets": _targets(request, warehouse),
            "transfers": transfers,
            "today": timezone.localdate(),
        })

    def post(self, request, pk):
        warehouse = _source_warehouse(request, pk)
        try:
            data = json.loads(request.body or "{}")
            target = Warehouse.objects.select_related("accounting_book").get(
                pk=int(data.get("to_warehouse")))
            roll_ids = [int(x) for x in (data.get("roll_ids") or [])]
            day = _date.fromisoformat(data["date"]) if data.get("date") else None
        except (ValueError, TypeError, Warehouse.DoesNotExist):
            return JsonResponse({"success": False, "error": _("Pick the warehouse the stock goes to.")},
                                status=400)
        if target.pk not in {w.pk for w in _targets(request, warehouse)}:
            return JsonResponse({"success": False, "error": _("Pick the warehouse the stock goes to.")},
                                status=400)
        try:
            transfer = transfer_stock(
                warehouse, target, roll_ids, user=request.user, member=_member(request),
                date=day, note=(data.get("note") or "").strip())
        except TransferError as exc:
            return JsonResponse({"success": False, "error": exc.message, "blocked": exc.blocked},
                                status=422)
        return JsonResponse({
            "success": True,
            "url": reverse("operating:stock_transfer_detail", args=[transfer.pk]),
        })


# How many codes one request may name. A pasted column is a shipment's
# worth of rolls, not a warehouse's.
FIND_LIMIT = 1000


def _find_rolls(warehouse, code):
    """(rolls, why_not) for one scanned or typed code: the one roll carrying
    that barcode, else every live roll of the product with that SKU or
    barcode."""
    related = ("product", "product__warehouse", "purchase_invoice_item")
    rolls = list(WarehouseProductItem.objects.filter(barcode__iexact=code)
                 .select_related(*related))
    if rolls and rolls[0].product.warehouse_id != warehouse.pk:
        return [], (_("This stock item is in %(warehouse)s, not here.")
                    % {"warehouse": rolls[0].product.warehouse.name})
    if not rolls:
        products = WarehouseProduct.objects.filter(warehouse=warehouse).filter(
            Q(sku__iexact=code) | Q(barcode__iexact=code))
        rolls = list(WarehouseProductItem.objects
                     .filter(product__in=products).exclude(status="consumed")
                     .select_related(*related)
                     .order_by("barcode", "pk")[:500])
    if not rolls:
        return [], _("Nothing in this warehouse carries that code.")
    return rolls, ""


@login_required
def stock_transfer_find(request, pk):
    """The rolls a scan, a typed code or a pasted list names in this
    warehouse. A code that names nothing is handed back with the reason,
    so one bad line does not lose the rest of a list."""
    warehouse = _source_warehouse(request, pk)
    if request.method == "POST":
        try:
            codes = json.loads(request.body or "{}").get("codes") or []
        except ValueError:
            codes = []
    else:
        codes = [request.GET.get("q") or ""]
    codes = list(dict.fromkeys(c.strip() for c in codes if isinstance(c, str) and c.strip()))
    if not codes:
        return JsonResponse({"success": False, "error": _("Scan or type a barcode or SKU.")}, status=400)
    if len(codes) > FIND_LIMIT:
        return JsonResponse({
            "success": False,
            "error": _("That is more than %(limit)s codes — add them in smaller lists.")
            % {"limit": FIND_LIMIT}}, status=400)

    found, skipped = {}, []
    for code in codes:
        rolls, why = _find_rolls(warehouse, code)
        if why:
            skipped.append({"code": code, "why": str(why)})
        for roll in rolls:
            found.setdefault(roll.pk, roll)
    return JsonResponse({"success": True,
                         "rolls": [_roll_row(r) for r in found.values()],
                         "skipped": skipped})


def _transfer_for(request, pk):
    """A transfer, for a member of either book it touched."""
    transfer = get_object_or_404(
        StockTransfer.objects.select_related(
            "from_warehouse", "to_warehouse", "from_book", "to_book", "purchase",
            "created_by", "undone_by"), pk=pk)
    from erp.roles import is_sales_rep
    member = _member(request)
    if is_sales_rep(request.user) or not (member_can_use_book(member, transfer.from_book)
                                          or member_can_use_book(member, transfer.to_book)):
        raise Http404("No such record.")
    return transfer


@login_required
def stock_transfer_detail(request, pk):
    transfer = _transfer_for(request, pk)
    member = _member(request)
    lines = list(transfer.lines.all())
    # Back to whichever end of it the viewer works in.
    if _may_transfer(request, transfer.from_book):
        back_url = reverse("operating:stock_transfer_create", args=[transfer.from_warehouse_id])
    else:
        back_url = reverse("operating:warehouse_detail", args=[transfer.to_warehouse_id])
    return render(request, "operating/stock_transfer_detail.html", {
        "transfer": transfer,
        "back_url": back_url,
        "lines": lines,
        "meters": sum((l.quantity for l in lines), Decimal("0")),
        "sees_purchase": member_can_use_book(member, transfer.to_book),
        "can_undo": (not transfer.is_undone
                     and _may_transfer(request, transfer.from_book, transfer.to_book)),
    })


@login_required
def stock_transfer_undo(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required."}, status=405)
    transfer = _transfer_for(request, pk)
    if not _may_transfer(request, transfer.from_book, transfer.to_book):
        raise Http404("No such record.")
    try:
        undo_stock_transfer(transfer, user=request.user, member=_member(request))
    except TransferError as exc:
        return JsonResponse({"success": False, "error": exc.message, "blocked": exc.blocked},
                            status=422)
    return JsonResponse({"success": True})
