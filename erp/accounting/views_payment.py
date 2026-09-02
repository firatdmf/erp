"""
Payment views (Phase 3).

    /accounting/accounts/payments/                   → PaymentList
    /accounting/accounts/payments/new/?account=<id>  → PaymentCreate (open invoices auto-listed)
    /accounting/accounts/payments/<id>/              → PaymentDetail
    /accounting/accounts/payments/<id>/edit/         → PaymentEdit (draft or confirmed)
    /accounting/accounts/payments/<id>/confirm/      → PaymentConfirm (POST)
    /accounting/accounts/payments/<id>/cancel/       → PaymentCancel (POST)
    /accounting/accounts/payments/<id>/delete/       → PaymentDelete (draft only, POST)

The create form receives allocations as JSON in the `allocations_json` field:
    [{"invoice_id": 12, "amount": "150.00"}, {"invoice_id": null, "amount": "50.00"}]
"""
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
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


def _entered_rate(request):
    """The rate typed on the form, or None if the field was left alone.

    None means "nobody said", which is what lets the published rate for the
    date apply instead. Zero and unparseable input mean the same thing —
    they cannot be a rate, and treating them as one would convert the
    payment to nothing.
    """
    raw = (request.POST.get("exchange_rate") or "").strip()
    if not raw:
        return None
    try:
        rate = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    return rate if rate > 0 else None


def _shift_cash(cash_account_id, delta):
    """Move a cash account balance by `delta` with a raw UPDATE, the same
    way Payment.confirm() does — going through save() would run
    CashAccount.clean()."""
    if cash_account_id and delta:
        CashAccount.objects.filter(pk=cash_account_id).update(
            balance=F("balance") + delta
        )


def _next_payment_number(book, ptype):
    """Generate COL-2026-000001 / PAY-2026-000001.

    These used to be TAH (tahsilat) and OD (ödeme); the documents already
    carrying those prefixes keep them. The sequence itself is shared and
    carries straight on, so renaming the prefixes leaves no gap.
    """
    settings_obj = CariSettings.for_book(book)
    prefix = "COL" if ptype in ("collection", "refund_out") else "PAY"
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

    # Both free-text filters fold each side to plain uppercase ASCII —
    # cari names are stored in uppercase Turkish, ILIKE folds only ASCII
    # case, and "gurhan" has to find GÜRHAN whatever keyboard produced it.
    from .views_accounts import tr_fold, tr_fold_expr

    qs = qs.annotate(
        _f_name=tr_fold_expr("cari__name"),
        _f_code=tr_fold_expr("cari__code"),
    )

    q = (request.GET.get("q") or "").strip()
    if q:
        needle = tr_fold(q)
        qs = qs.filter(
            Q(_f_name__contains=needle)
            | Q(_f_code__contains=needle)
            | Q(number__icontains=q)
            | Q(description__icontains=q)
        )

    cari_id = request.GET.get("account") or ""
    if cari_id.isdigit():
        qs = qs.filter(cari_id=int(cari_id))

    # Free-text cari filter: matches against name OR code so the user
    # doesn't have to remember the exact spelling. Anchored by the
    # filter bar's "Account" input.
    cari_q = (request.GET.get("cari_q") or "").strip()
    if cari_q:
        needle = tr_fold(cari_q)
        qs = qs.filter(Q(_f_name__contains=needle) | Q(_f_code__contains=needle))

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
    template_name = "accounts/payment_list.html"

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
            return render(request, "accounts/partials/payment_list_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
@login_required
def fx_rate_lookup(request):
    """The published rate for a currency pair on a given day, as JSON.

    Used by the payment form to show what a foreign-currency amount comes to
    in the book's own currency before it is saved. The form may override the
    number it gets back — whoever is entering the payment may well know the
    rate they actually got better than any published source does.

    Always answers 200. A rate that cannot be fetched is a blank field on the
    form for the user to fill in themselves, not an error to interrupt them
    with.
    """
    from accounting.services import get_exchange_rate

    source = (request.GET.get("from") or "").upper()
    target = (request.GET.get("to") or "").upper()
    if not source or not target:
        return JsonResponse({"rate": None, "reason": "currency missing"})
    if source == target:
        # No conversion to make; the form hides the row entirely.
        return JsonResponse({"rate": None, "reason": "same currency"})

    on_date = parse_date(request.GET.get("date") or "") or timezone.localdate()
    try:
        rate = get_exchange_rate(source, target, on_date=on_date)
    except Exception:
        rate = None
    return JsonResponse({
        "rate": str(rate) if rate else None,
        "date": on_date.isoformat(),
    })


def _fx_context(book):
    """What the form's converter needs, as JSON for the script tag.

    "null" when there is no book yet — the account has not been picked — and
    the script reads that as nothing to convert to and stays out of the way.
    """
    if book is None:
        return "null"
    base = book.effective_base_currency
    return json.dumps({"id": base.pk, "code": base.code, "symbol": base.symbol})


# Create
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentCreate(View):
    template_name = "accounts/payment_form.html"

    def get(self, request):
        prefilled_cari = None
        cari_id = request.GET.get("account")
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

        # "Take Payment" / "Make Payment" land here with ?type= so the
        # form opens on the right side without the user re-picking it.
        initial_type = request.GET.get("type")
        if initial_type not in dict(Payment.PAYMENT_TYPES):
            initial_type = "collection"

        return render(request, self.template_name, {
            "payment": None,
            "prefilled_cari": prefilled_cari,
            "cari_options": cari_options,
            "cash_accounts": cash_qs,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices":   Payment.PAYMENT_TYPES,
            "method_choices": Payment.METHOD_CHOICES,
            "initial_type":   initial_type,
            "base_currency": _fx_context(prefilled_cari.book if prefilled_cari else None),
            "open_invoices_json": json.dumps(_serialize_invoices(open_invoices), default=str),
        })

    def post(self, request):
        cari_id = request.POST.get("account")
        if not cari_id:
            messages.error(request, _g("An account must be selected."))
            return redirect("accounts:payment_create", book_id=request.book.pk)
        cari = get_object_or_404(CariAccount, pk=int(cari_id))

        amount = _D(request.POST.get("amount"))
        if amount <= 0:
            messages.error(request, _g("Amount must be greater than zero."))
            return redirect("accounts:payment_create", book_id=request.book.pk)

        try:
            allocations = _parse_allocations(request.POST.get("allocations_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("accounts:payment_create", book_id=request.book.pk)

        # Verify sum of allocations <= amount
        total_alloc = sum((a["amount"] for a in allocations), Decimal("0"))
        if total_alloc > amount + Decimal("0.01"):
            messages.error(request,
                           _g("Allocation total (%(total)s) cannot exceed payment amount (%(amount)s).")
                           % {"total": total_alloc, "amount": amount})
            return redirect("accounts:payment_create", book_id=request.book.pk)

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
                exchange_rate=_entered_rate(request),
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
        return redirect("accounts:payment_detail", pk=payment.pk)


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
    template_name = "accounts/payment_detail.html"

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
# Edit
# ---------------------------------------------------------------------------
def _edit_invoice_rows(payment):
    """Invoice rows for the edit form: everything still open on the account,
    plus whatever this payment is already applied to — a fully-paid invoice
    is no longer "open", but its allocation still has to be visible and
    editable here.

    A confirmed payment has already paid its allocations down, so the
    balance shown adds that share back; otherwise each row would cap the
    input at what is left AFTER this very payment.
    """
    applied = defaultdict(lambda: Decimal("0.00"))
    for inv_id, amt in payment.allocations.exclude(invoice=None).values_list("invoice_id", "amount"):
        applied[inv_id] += amt

    rows = (payment.cari.invoices
            .filter(Q(status__in=["issued", "partially_paid", "overdue"])
                    | Q(pk__in=list(applied)))
            .exclude(status="cancelled")
            .order_by("date", "id")
            .values("id", "series", "number", "date", "due_date", "total", "balance",
                    "currency__code", "type"))

    out = _serialize_invoices(rows)
    already_counted = payment.status == "confirmed"
    for row in out:
        share = applied.get(row["id"], Decimal("0.00"))
        row["applied"] = str(share)
        if already_counted:
            row["balance"] = str(Decimal(row["balance"]) + share)
    return out


@method_decorator(login_required, name="dispatch")
class PaymentEdit(View):
    """Edit a draft or a confirmed payment.

    A confirmed payment has already moved money — it posted a
    CariMovement, shifted a cash account balance and paid invoices down —
    so an edit has to walk all three back and re-apply them: the ledger
    row is refreshed in place (resync_posted_movement), the old cash
    effect is reversed before the new one lands, and every invoice on
    either the old or the new allocation set is recomputed.

    Cancelled payments are terminal, exactly as with invoices: no edit.
    The account can't be switched either — moving a posted payment to a
    different cari is a new document, not an edit.
    """
    template_name = "accounts/payment_form.html"

    def _block_if_cancelled(self, request, payment):
        if payment.status == "cancelled":
            messages.warning(request, _g("Cancelled payments can't be edited. Create a new one if needed."))
            return redirect("accounts:payment_detail", pk=payment.pk)
        return None

    def get(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related("cari", "book", "currency"), pk=pk)
        blocked = self._block_if_cancelled(request, payment)
        if blocked:
            return blocked

        # Cash accounts of the account's own book — plus whichever one the
        # payment already points at, so an out-of-book pick made earlier
        # isn't silently dropped by a select that can't show it.
        cash_qs = (CashAccount.objects
                   .select_related("currency", "book")
                   .filter(Q(book=payment.cari.book) | Q(pk=payment.cash_account_id))
                   .order_by("book", "name"))

        return render(request, self.template_name, {
            "payment": payment,
            "prefilled_cari": payment.cari,
            "cari_options": CariAccount.objects.none(),
            "cash_accounts": cash_qs,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices":   Payment.PAYMENT_TYPES,
            "method_choices": Payment.METHOD_CHOICES,
            "base_currency": _fx_context(payment.book or payment.cari.book),
            "open_invoices_json": json.dumps(_edit_invoice_rows(payment), default=str),
        })

    def post(self, request, pk):
        payment = get_object_or_404(Payment.objects.select_related("cari", "currency"), pk=pk)
        blocked = self._block_if_cancelled(request, payment)
        if blocked:
            return blocked

        amount = _D(request.POST.get("amount"))
        if amount <= 0:
            messages.error(request, _g("Amount must be greater than zero."))
            return redirect("accounts:payment_edit", pk=pk)

        try:
            allocations = _parse_allocations(request.POST.get("allocations_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("accounts:payment_edit", pk=pk)

        total_alloc = sum((a["amount"] for a in allocations), Decimal("0"))
        if total_alloc > amount + Decimal("0.01"):
            messages.error(request,
                           _g("Allocation total (%(total)s) cannot exceed payment amount (%(amount)s).")
                           % {"total": total_alloc, "amount": amount})
            return redirect("accounts:payment_edit", pk=pk)

        was_confirmed  = payment.status == "confirmed"
        old_cash_id    = payment.cash_account_id
        old_cash_delta = payment.amount * Decimal(payment.cash_sign)
        # Invoices to re-derive afterwards: the ones this payment is coming
        # off of as well as the ones it is landing on.
        touched = set(payment.allocations.exclude(invoice=None)
                      .values_list("invoice_id", flat=True))

        with transaction.atomic():
            payment.type   = request.POST.get("type")   or payment.type
            payment.method = request.POST.get("method") or payment.method
            payment.date   = request.POST.get("date")   or payment.date
            payment.amount = amount
            currency_id = request.POST.get("currency")
            if currency_id:
                payment.currency_id = int(currency_id)
            cash_account_id = request.POST.get("cash_account") or None
            payment.cash_account_id = int(cash_account_id) if cash_account_id else None
            payment.exchange_rate = _entered_rate(request)
            payment.description = request.POST.get("description", "")
            payment.notes = request.POST.get("notes", "")
            # `number` deliberately stays as issued, prefix and all: a
            # document number is what people quote back at you, so a type
            # change must not silently renumber it.
            payment.save()

            # Allocations are rebuilt wholesale — same shape as create.
            payment.allocations.all().delete()
            for a in allocations:
                inv = None
                if a["invoice_id"]:
                    inv = (Invoice.objects.filter(pk=a["invoice_id"], cari=payment.cari)
                           .exclude(status="cancelled").first())
                    if not inv:
                        continue  # invoice not found / wrong cari / cancelled → skip silently
                    touched.add(inv.pk)
                PaymentAllocation.objects.create(
                    payment=payment,
                    invoice=inv,
                    amount=a["amount"],
                )

            if was_confirmed:
                # Reverse what the old figures put on the cash side (which
                # may have been a different account entirely), then apply
                # the new ones.
                _shift_cash(old_cash_id, -old_cash_delta)
                _shift_cash(payment.cash_account_id,
                            payment.amount * Decimal(payment.cash_sign))
                # ...and move the cash ledger row with it. Without this the
                # balance changed while the transactions page showed nothing,
                # which is exactly what linking an account after the fact
                # used to do: the money appeared, the row never did.
                payment.sync_cash_entry()

            payment.resync_posted_movement(user=request.user)

            if request.POST.get("auto_confirm") == "1" and payment.status == "draft":
                try:
                    payment.confirm(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Saved but could not be confirmed: %(error)s") % {"error": ve})

            for inv in Invoice.objects.filter(pk__in=touched):
                inv.recompute_payment(save=True)

        messages.success(request, _g("Payment updated: %(number)s") % {"number": payment.number})
        return redirect("accounts:payment_detail", pk=payment.pk)


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
        return redirect("accounts:payment_detail", pk=payment.pk)


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
        return redirect("accounts:payment_detail", pk=payment.pk)


# ---------------------------------------------------------------------------
# Delete (draft only)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class PaymentDelete(View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status != "draft":
            messages.error(request, _g("Only draft payments can be deleted. Cancel confirmed payments instead."))
            return redirect("accounts:payment_detail", pk=payment.pk)
        label = payment.number
        book_id = payment.book_id       # read before the row goes
        payment.delete()
        messages.success(request, _g("Draft payment deleted: %(label)s") % {"label": label})
        return redirect("accounts:payment_list", book_id=book_id)
