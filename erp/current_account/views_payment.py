"""
Payment views (Phase 3).

    /cari/tahsilat/                       → PaymentList
    /cari/tahsilat/yeni/?cari=<id>        → PaymentCreate (open invoices auto-listed)
    /cari/tahsilat/<id>/                  → PaymentDetail
    /cari/tahsilat/<id>/onayla/           → PaymentConfirm (POST)
    /cari/tahsilat/<id>/iptal/            → PaymentCancel (POST)
    /cari/tahsilat/<id>/sil/              → PaymentDelete (draft only, POST)

The create form receives allocations as JSON in the `allocations_json` field:
    [{"invoice_id": 12, "amount": "150.00"}, {"invoice_id": null, "amount": "50.00"}]
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

from accounting.models import CashAccount, CurrencyCategory
from .models import (
    CariAccount,
    CariSettings,
    Invoice,
    Payment,
    PaymentAllocation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _D(val, default="0"):
    try:
        return Decimal(str(val if val not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _parse_allocations(raw):
    """Parse the allocations_json. Returns list of dicts; raises ValueError on bad input."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(_g("Could not parse allocations JSON: %(error)s") % {"error": e})
    if not isinstance(data, list):
        raise ValueError(_g("Allocations must be a list."))
    out = []
    for raw_alloc in data:
        if not isinstance(raw_alloc, dict):
            continue
        amount = _D(raw_alloc.get("amount"))
        if amount <= 0:
            continue
        invoice_id = raw_alloc.get("invoice_id")
        out.append({
            "invoice_id": int(invoice_id) if invoice_id else None,
            "amount": amount,
        })
    return out


def _next_payment_number(book, ptype):
    """Generate TAH-2026-000001 / OD-2026-000001."""
    settings_obj = CariSettings.for_book(book)
    prefix = "TAH" if ptype in ("collection", "refund_out") else "OD"
    with transaction.atomic():
        locked = CariSettings.objects.select_for_update().get(pk=settings_obj.pk)
        year = timezone.now().year
        number = f"{prefix}-{year}-{str(locked.next_payment_seq).zfill(6)}"
        locked.next_payment_seq += 1
        locked.save(update_fields=["next_payment_seq"])
    return number


def _filter_payments(request):
    qs = (Payment.objects
          .select_related("cari", "book", "currency", "cash_account")
          .all())

    # Turkish-aware case folding (ı↔I, i↔İ) for both free-text filters —
    # cari names are stored uppercase Turkish and SQL ILIKE only folds
    # ASCII, so a lowercase search would otherwise never match them.
    from .views import _tr_case_variants

    q = (request.GET.get("q") or "").strip()
    if q:
        cond = Q()
        for v in _tr_case_variants(q):
            cond |= (
                Q(number__icontains=v)
                | Q(cari__name__icontains=v)
                | Q(cari__code__icontains=v)
                | Q(description__icontains=v)
            )
        qs = qs.filter(cond)

    cari_id = request.GET.get("cari") or ""
    if cari_id.isdigit():
        qs = qs.filter(cari_id=int(cari_id))

    # Free-text cari filter: matches against name OR code so the user
    # doesn't have to remember the exact spelling. Anchored by the
    # filter bar's "Account" input.
    cari_q = (request.GET.get("cari_q") or "").strip()
    if cari_q:
        cond = Q()
        for v in _tr_case_variants(cari_q):
            cond |= Q(cari__name__icontains=v) | Q(cari__code__icontains=v)
        qs = qs.filter(cond)

    type_ = request.GET.get("type") or ""
    if type_ in dict(Payment.PAYMENT_TYPES):
        qs = qs.filter(type=type_)

    # Direction (Giriş / Çıkış) — money flow as seen by the company.
    # Inflows = collections from customers + refunds from suppliers.
    # Outflows = payments to suppliers + refunds to customers.
    direction = (request.GET.get("direction") or "").strip()
    if direction == "in":
        qs = qs.filter(type__in=["collection", "refund_out"])
    elif direction == "out":
        qs = qs.filter(type__in=["payment", "refund_in"])

    status_ = request.GET.get("status") or ""
    if status_ in dict(Payment.STATUS_CHOICES):
        qs = qs.filter(status=status_)

    date_from = request.GET.get("date_from") or ""
    date_to   = request.GET.get("date_to")   or ""
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    return qs.order_by("-date", "-id")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentList(View):
    template_name = "current_account/payment_list.html"

    def get(self, request):
        qs = _filter_payments(request)
        totals = qs.aggregate(
            n=Count("id"),
            collection_sum=Sum("amount", filter=Q(type__in=["collection", "refund_out"],
                                                   status="confirmed")),
            payment_sum=Sum("amount", filter=Q(type__in=["payment", "refund_in"],
                                                status="confirmed")),
        )
        ctx = {
            "payments":     qs[:500],
            "n":            totals["n"] or 0,
            "collection_sum": totals["collection_sum"] or Decimal("0.00"),
            "payment_sum":    totals["payment_sum"]    or Decimal("0.00"),
            "type_choices":   Payment.PAYMENT_TYPES,
            "status_choices": Payment.STATUS_CHOICES,
            "q":            request.GET.get("q", ""),
            "filter_type":  request.GET.get("type", ""),
            "filter_status":request.GET.get("status", ""),
            "filter_cari_q":request.GET.get("cari_q", ""),
            "filter_direction": request.GET.get("direction", ""),
            "date_from":    request.GET.get("date_from", ""),
            "date_to":      request.GET.get("date_to", ""),
        }
        # Live search — the page JS refetches with X-Requested-With and
        # swaps ONLY the results block (stats + count + table), no reload.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(request, "current_account/partials/payment_list_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentCreate(View):
    template_name = "current_account/payment_form.html"

    def get(self, request):
        prefilled_cari = None
        cari_id = request.GET.get("cari")
        if cari_id and cari_id.isdigit():
            prefilled_cari = CariAccount.objects.filter(pk=int(cari_id)).first()

        cari_options = (
            CariAccount.objects.filter(is_active=True).order_by("name")
            if not prefilled_cari else CariAccount.objects.none()
        )

        # Open invoices for the prefilled cari
        open_invoices = []
        if prefilled_cari:
            open_invoices = list(
                prefilled_cari.invoices
                .filter(status__in=["issued", "partially_paid", "overdue"])
                .order_by("date", "id")
                .values("id", "series", "number", "date", "due_date", "total", "balance",
                        "currency__code", "type")
            )

        # Cash accounts scoped to prefilled cari's book if known
        cash_qs = CashAccount.objects.select_related("currency", "book").all().order_by("book", "name")
        if prefilled_cari:
            cash_qs = cash_qs.filter(book=prefilled_cari.book)

        return render(request, self.template_name, {
            "payment": None,
            "prefilled_cari": prefilled_cari,
            "cari_options": cari_options,
            "cash_accounts": cash_qs,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices":   Payment.PAYMENT_TYPES,
            "method_choices": Payment.METHOD_CHOICES,
            "open_invoices_json": json.dumps(_serialize_invoices(open_invoices), default=str),
        })

    def post(self, request):
        cari_id = request.POST.get("cari")
        if not cari_id:
            messages.error(request, _g("An account must be selected."))
            return redirect("current_account:payment_create")
        cari = get_object_or_404(CariAccount, pk=int(cari_id))

        amount = _D(request.POST.get("amount"))
        if amount <= 0:
            messages.error(request, _g("Amount must be greater than zero."))
            return redirect("current_account:payment_create")

        try:
            allocations = _parse_allocations(request.POST.get("allocations_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("current_account:payment_create")

        # Verify sum of allocations <= amount
        total_alloc = sum((a["amount"] for a in allocations), Decimal("0"))
        if total_alloc > amount + Decimal("0.01"):
            messages.error(request,
                           _g("Allocation total (%(total)s) cannot exceed payment amount (%(amount)s).")
                           % {"total": total_alloc, "amount": amount})
            return redirect("current_account:payment_create")

        ptype = request.POST.get("type") or "collection"
        method = request.POST.get("method") or "bank_transfer"
        currency_id = int(request.POST.get("currency") or cari.default_currency_id)
        cash_account_id = request.POST.get("cash_account") or None

        with transaction.atomic():
            payment = Payment.objects.create(
                cari=cari,
                book=cari.book,
                number=_next_payment_number(cari.book, ptype),
                type=ptype,
                method=method,
                status="draft",
                date=request.POST.get("date") or timezone.now().date(),
                amount=amount,
                currency_id=currency_id,
                cash_account_id=int(cash_account_id) if cash_account_id else None,
                description=request.POST.get("description", ""),
                notes=request.POST.get("notes", ""),
                created_by=getattr(request.user, "member", None),
            )

            # Create allocations
            for a in allocations:
                inv = None
                if a["invoice_id"]:
                    # Cancelled invoices are terminal (no restore path) — money
                    # allocated onto one could never be reconciled again.
                    inv = (Invoice.objects.filter(pk=a["invoice_id"], cari=cari)
                           .exclude(status="cancelled").first())
                    if not inv:
                        continue  # invoice not found / wrong cari / cancelled → skip silently
                PaymentAllocation.objects.create(
                    payment=payment,
                    invoice=inv,
                    amount=a["amount"],
                )

            # Auto-confirm if requested
            if request.POST.get("auto_confirm") == "1":
                try:
                    payment.confirm(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Saved but could not be confirmed: %(error)s") % {"error": ve})

        messages.success(request, _g("Payment created: %(number)s") % {"number": payment.number})
        return redirect("current_account:payment_detail", pk=payment.pk)


def _serialize_invoices(invoices_qs_or_dicts):
    """Convert invoice queryset/values to a JSON-friendly list for the form."""
    out = []
    for inv in invoices_qs_or_dicts:
        out.append({
            "id": inv["id"],
            "label": f"{inv['series']}-{inv['number']}",
            "type": inv["type"],
            "date": inv["date"].isoformat() if inv["date"] else "",
            "due_date": inv["due_date"].isoformat() if inv["due_date"] else "",
            "total": str(inv["total"]),
            "balance": str(inv["balance"]),
            "currency": inv["currency__code"],
        })
    return out


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentDetail(View):
    template_name = "current_account/payment_detail.html"

    def get(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related("cari", "book", "currency", "cash_account",
                                           "posted_movement"),
            pk=pk,
        )
        allocations = (
            payment.allocations
            .select_related("invoice")
            .order_by("id")
        )
        return render(request, self.template_name, {
            "payment": payment,
            "allocations": allocations,
        })


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentConfirm(View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        try:
            payment.confirm(user=request.user)
            messages.success(request, _g("Payment confirmed: %(number)s") % {"number": payment.number})
        except ValidationError as ve:
            messages.error(request, _g("Confirmation failed: %(error)s") % {"error": ve})
        return redirect("current_account:payment_detail", pk=payment.pk)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentCancel(View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        reason = request.POST.get("reason", "")
        payment.cancel(user=request.user, reason=reason)
        messages.success(request, _g("Payment cancelled."))
        # Cancelled from the list? Go back there (filters intact) instead
        # of bouncing to the detail page. Internal paths only.
        nxt = (request.POST.get("next") or "").strip()
        if nxt.startswith("/") and not nxt.startswith("//"):
            return redirect(nxt)
        return redirect("current_account:payment_detail", pk=payment.pk)


# ---------------------------------------------------------------------------
# Delete (draft only)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentDelete(View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status != "draft":
            messages.error(request, _g("Only draft payments can be deleted. Cancel confirmed payments instead."))
            return redirect("current_account:payment_detail", pk=payment.pk)
        label = payment.number
        payment.delete()
        messages.success(request, _g("Draft payment deleted: %(label)s") % {"label": label})
        return redirect("current_account:payment_list")
