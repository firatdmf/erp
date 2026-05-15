"""
Invoice views (Phase 2).

    /cari/fatura/                       → InvoiceList
    /cari/fatura/yeni/                  → InvoiceCreate (with line items)
    /cari/fatura/yeni/?cari=<id>        → InvoiceCreate prefilled for a cari
    /cari/fatura/<id>/                  → InvoiceDetail
    /cari/fatura/<id>/duzenle/          → InvoiceEdit (draft only)
    /cari/fatura/<id>/kes/              → InvoiceIssue
    /cari/fatura/<id>/iptal/            → InvoiceCancel
    /cari/fatura/<id>/sil/              → InvoiceDelete (draft only)

The create/edit forms receive line items as JSON in the `items_json` field,
so the dynamic add/remove UX stays simple and reliable.
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import CurrencyCategory
from .models import (
    CariAccount,
    CariSettings,
    Invoice,
    InvoiceItem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_decimal(val, default="0"):
    try:
        return Decimal(str(val if val not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _parse_items(items_json):
    """Parse the items_json field. Returns list of dicts; raises ValueError on bad input."""
    if not items_json:
        return []
    try:
        data = json.loads(items_json)
    except json.JSONDecodeError as e:
        raise ValueError(_g("Could not parse items JSON: %(error)s") % {"error": e})
    if not isinstance(data, list):
        raise ValueError(_g("Items must be a list."))
    out = []
    for i, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            continue
        desc = (raw.get("description") or "").strip()
        if not desc:
            continue
        out.append({
            "line_no":       i,
            "description":   desc[:300],
            "product_id":    raw.get("product_id") or None,
            "variant_id":    raw.get("variant_id") or None,
            "quantity":      _parse_decimal(raw.get("quantity"), "1"),
            "unit":          (raw.get("unit") or "adet")[:20],
            "unit_price":    _parse_decimal(raw.get("unit_price")),
            "discount_rate": _parse_decimal(raw.get("discount_rate")),
            "tax_rate":      _parse_decimal(raw.get("tax_rate"), "20"),
        })
    return out


def _filter_invoices(request):
    qs = Invoice.objects.select_related("cari", "book", "currency").all()

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(cari__name__icontains=q)
            | Q(cari__code__icontains=q)
            | Q(notes__icontains=q)
        )

    cari_id = request.GET.get("cari") or ""
    if cari_id.isdigit():
        qs = qs.filter(cari_id=int(cari_id))

    book_id = request.GET.get("book") or ""
    if book_id.isdigit():
        qs = qs.filter(book_id=int(book_id))

    type_ = request.GET.get("type") or ""
    if type_ in dict(Invoice.INVOICE_TYPES):
        qs = qs.filter(type=type_)

    status_ = request.GET.get("status") or ""
    if status_ in dict(Invoice.STATUS_CHOICES):
        qs = qs.filter(status=status_)

    date_from = request.GET.get("date_from") or ""
    date_to   = request.GET.get("date_to") or ""
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    return qs.order_by("-date", "-id")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceList(View):
    template_name = "current_account/invoice_list.html"

    def get(self, request):
        qs = _filter_invoices(request)

        totals = qs.aggregate(
            n=Count("id"),
            total_sum=Sum("total"),
            unpaid_sum=Sum("balance"),
        )

        from accounting.models import Book
        ctx = {
            "invoices":    qs[:500],
            "n":           totals["n"] or 0,
            "total_sum":   totals["total_sum"]  or Decimal("0.00"),
            "unpaid_sum":  totals["unpaid_sum"] or Decimal("0.00"),
            "books":       Book.objects.all(),
            "type_choices":   Invoice.INVOICE_TYPES,
            "status_choices": Invoice.STATUS_CHOICES,
            "q":           request.GET.get("q", ""),
            "filter_book": request.GET.get("book", ""),
            "filter_type": request.GET.get("type", ""),
            "filter_status": request.GET.get("status", ""),
            "filter_cari": request.GET.get("cari", ""),
            "date_from":   request.GET.get("date_from", ""),
            "date_to":     request.GET.get("date_to", ""),
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceCreate(View):
    template_name = "current_account/invoice_form.html"

    def get(self, request):
        prefilled_cari = None
        cari_id = request.GET.get("cari")
        if cari_id and cari_id.isdigit():
            prefilled_cari = CariAccount.objects.filter(pk=int(cari_id)).first()

        cari_options = (
            CariAccount.objects.filter(is_active=True).order_by("name")
            if not prefilled_cari else CariAccount.objects.none()
        )

        return render(request, self.template_name, {
            "invoice": None,
            "prefilled_cari": prefilled_cari,
            "cari_options": cari_options,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices": Invoice.INVOICE_TYPES,
            "default_due_days": 30,
            "items_json": "[]",
        })

    def post(self, request):
        cari_id = request.POST.get("cari")
        if not cari_id:
            messages.error(request, _g("An account must be selected."))
            return redirect("current_account:invoice_create")

        cari = get_object_or_404(CariAccount, pk=int(cari_id))

        # Parse items first — bail early if invalid
        try:
            items_data = _parse_items(request.POST.get("items_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("current_account:invoice_create")
        if not items_data:
            messages.error(request, _g("You must add at least one invoice item."))
            return redirect("current_account:invoice_create")

        invoice_type = request.POST.get("type") or "sales"
        series = request.POST.get("series") or "FAT"
        currency_id = int(request.POST.get("currency") or cari.default_currency_id)

        settings_obj = CariSettings.for_book(cari.book)
        number = settings_obj.next_invoice_number(series=series)

        try:
            date = request.POST.get("date") or timezone.now().date().isoformat()
            due_date = request.POST.get("due_date")
            if not due_date:
                # Default to cari payment_term_days
                from datetime import date as _date, timedelta
                d = _date.fromisoformat(date)
                due_date = (d + timedelta(days=cari.payment_term_days)).isoformat()
        except ValueError:
            messages.error(request, _g("Invalid date."))
            return redirect("current_account:invoice_create")

        with transaction.atomic():
            invoice = Invoice.objects.create(
                cari=cari,
                book=cari.book,
                series=series,
                number=number,
                type=invoice_type,
                status="draft",
                date=date,
                due_date=due_date,
                delivery_date=request.POST.get("delivery_date") or None,
                currency_id=currency_id,
                other_charges=_parse_decimal(request.POST.get("other_charges")),
                notes=request.POST.get("notes", ""),
                created_by=getattr(request.user, "member", None),
            )
            for item in items_data:
                InvoiceItem.objects.create(invoice=invoice, **item)
            invoice.recompute_totals(save=True)

            # Auto-issue if requested
            if request.POST.get("auto_issue") == "1":
                try:
                    invoice.issue(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Invoice created but could not be issued: %(error)s") % {"error": ve})

        messages.success(request, _g("Invoice created: %(series)s-%(number)s") % {"series": invoice.series, "number": invoice.number})
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Edit (draft only)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceEdit(View):
    template_name = "current_account/invoice_form.html"

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status != "draft":
            messages.warning(request, _g("Only draft invoices can be edited."))
            return redirect("current_account:invoice_detail", pk=pk)

        return render(request, self.template_name, {
            "invoice": invoice,
            "prefilled_cari": invoice.cari,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices": Invoice.INVOICE_TYPES,
            "items_json": json.dumps([{
                "description":   it.description,
                "product_id":    it.product_id,
                "variant_id":    it.variant_id,
                "quantity":      str(it.quantity),
                "unit":          it.unit,
                "unit_price":    str(it.unit_price),
                "discount_rate": str(it.discount_rate),
                "tax_rate":      str(it.tax_rate),
            } for it in invoice.items.order_by("line_no")]),
        })

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status != "draft":
            messages.error(request, _g("Only draft invoices can be edited."))
            return redirect("current_account:invoice_detail", pk=pk)

        try:
            items_data = _parse_items(request.POST.get("items_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("current_account:invoice_edit", pk=pk)
        if not items_data:
            messages.error(request, _g("You must add at least one invoice item."))
            return redirect("current_account:invoice_edit", pk=pk)

        with transaction.atomic():
            invoice.type = request.POST.get("type") or invoice.type
            invoice.date = request.POST.get("date") or invoice.date
            invoice.due_date = request.POST.get("due_date") or invoice.due_date
            invoice.delivery_date = request.POST.get("delivery_date") or None
            currency_id = request.POST.get("currency")
            if currency_id:
                invoice.currency_id = int(currency_id)
            invoice.other_charges = _parse_decimal(request.POST.get("other_charges"))
            invoice.notes = request.POST.get("notes", "")
            invoice.save()

            # Replace items wholesale (draft only — safe)
            invoice.items.all().delete()
            for item in items_data:
                InvoiceItem.objects.create(invoice=invoice, **item)
            invoice.recompute_totals(save=True)

            if request.POST.get("auto_issue") == "1":
                try:
                    invoice.issue(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Edited but could not be issued: %(error)s") % {"error": ve})

        messages.success(request, _g("Invoice updated."))
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceDetail(View):
    template_name = "current_account/invoice_detail.html"

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related("cari", "book", "currency", "order",
                                           "posted_movement"),
            pk=pk,
        )
        items = invoice.items.select_related("product", "variant").order_by("line_no")

        # Tax breakdown by rate (for the totals summary)
        tax_breakdown = {}
        for it in items:
            key = str(it.tax_rate)
            agg = tax_breakdown.setdefault(key, {"net": Decimal("0"), "tax": Decimal("0")})
            agg["net"] += (it.subtotal - it.discount_amount)
            agg["tax"] += it.tax_amount

        return render(request, self.template_name, {
            "invoice": invoice,
            "items":   items,
            "tax_breakdown": sorted(tax_breakdown.items()),
        })


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceIssue(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            invoice.issue(user=request.user)
            messages.success(request, _g("Invoice issued: %(series)s-%(number)s") % {"series": invoice.series, "number": invoice.number})
        except ValidationError as ve:
            messages.error(request, _g("Issue failed: %(error)s") % {"error": ve})
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceCancel(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        reason = request.POST.get("reason", "")
        invoice.cancel(user=request.user, reason=reason)
        messages.success(request, _g("Invoice cancelled."))
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Delete (draft only)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceDelete(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status != "draft":
            messages.error(request, _g("Only draft invoices can be deleted. Cancel issued invoices instead."))
            return redirect("current_account:invoice_detail", pk=invoice.pk)
        label = f"{invoice.series}-{invoice.number}"
        invoice.delete()
        messages.success(request, _g("Draft invoice deleted: %(label)s") % {"label": label})
        return redirect("current_account:invoice_list")
