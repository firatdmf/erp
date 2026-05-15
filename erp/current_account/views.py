"""
Views for current_account (Cari Hesap) — Phase 1.

    /cari/                  → CariList
    /cari/yeni/             → CariCreate
    /cari/<id>/             → CariDetail   (summary + tabs)
    /cari/<id>/ekstre/      → CariStatement (ekstre)
    /cari/<id>/duzenle/     → CariEdit
    /cari/<id>/sil/         → CariDelete
    /cari/<id>/hareket/yeni/→ CariMovementCreate (manual entry)
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import Book, CurrencyCategory
from .models import CariAccount, CariMovement, CariSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _books():
    return Book.objects.all().order_by("name")


def _currencies():
    return CurrencyCategory.objects.all().order_by("code")


def _filter_caris(request):
    qs = CariAccount.objects.select_related("book", "default_currency").all()

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(name__icontains=q)
            | Q(tax_number__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )

    book_id = request.GET.get("book") or ""
    if book_id.isdigit():
        qs = qs.filter(book_id=int(book_id))

    type_filter = request.GET.get("type") or ""
    if type_filter in dict(CariAccount.TYPE_CHOICES):
        qs = qs.filter(type=type_filter)

    balance_filter = request.GET.get("balance") or ""
    if balance_filter == "positive":      # bize borçlu
        qs = qs.filter(cached_balance__gt=0)
    elif balance_filter == "negative":    # bizden alacaklı
        qs = qs.filter(cached_balance__lt=0)
    elif balance_filter == "zero":
        qs = qs.filter(cached_balance=0)
    elif balance_filter == "over_limit":
        qs = qs.filter(cached_balance__gt=0).extra(
            where=["cached_balance > credit_limit AND credit_limit > 0"]
        )

    active = request.GET.get("active") or "1"
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)

    sort = request.GET.get("sort") or "name"
    sort_map = {
        "name":      "name",
        "-name":     "-name",
        "code":      "code",
        "-code":     "-code",
        "balance":   "cached_balance",
        "-balance":  "-cached_balance",
        "recent":    "-last_movement_at",
        "-recent":   "last_movement_at",
    }
    qs = qs.order_by(sort_map.get(sort, "name"))
    return qs


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariList(View):
    template_name = "current_account/cari_list.html"

    def get(self, request):
        qs = _filter_caris(request)

        # Aggregate totals across the filtered set (positive vs negative legs)
        totals = qs.aggregate(
            n=Count("id"),
            owes_us=Sum("cached_balance_base", filter=Q(cached_balance__gt=0)),
            we_owe=Sum("cached_balance_base", filter=Q(cached_balance__lt=0)),
        )

        ctx = {
            "caris":          qs[:500],
            "total_count":    totals["n"] or 0,
            "owes_us":        totals["owes_us"] or Decimal("0.00"),
            "we_owe":         abs(totals["we_owe"] or Decimal("0.00")),
            "net":            (totals["owes_us"] or Decimal("0.00")) + (totals["we_owe"] or Decimal("0.00")),
            "books":          _books(),
            "type_choices":   CariAccount.TYPE_CHOICES,
            "q":              request.GET.get("q", ""),
            "filter_book":    request.GET.get("book", ""),
            "filter_type":    request.GET.get("type", ""),
            "filter_balance": request.GET.get("balance", ""),
            "filter_active":  request.GET.get("active", "1"),
            "sort":           request.GET.get("sort", "name"),
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create / Edit
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariCreate(View):
    template_name = "current_account/cari_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "cari": None,
            "books": _books(),
            "currencies": _currencies(),
            "type_choices": CariAccount.TYPE_CHOICES,
        })

    def post(self, request):
        book_id = request.POST.get("book")
        currency_id = request.POST.get("default_currency")
        if not book_id or not currency_id:
            messages.error(request, _g("Book and currency are required."))
            return redirect("current_account:cari_create")

        cari = CariAccount(
            book_id=int(book_id),
            name=request.POST.get("name", "").strip(),
            type=request.POST.get("type", "customer"),
            default_currency_id=int(currency_id),
            payment_term_days=int(request.POST.get("payment_term_days") or 30),
            credit_limit=Decimal(request.POST.get("credit_limit") or "0"),
            discount_rate=Decimal(request.POST.get("discount_rate") or "0"),
            opening_balance=Decimal(request.POST.get("opening_balance") or "0"),
            opening_balance_date=request.POST.get("opening_balance_date") or None,
            tax_office=request.POST.get("tax_office", ""),
            tax_number=request.POST.get("tax_number", ""),
            identity_number=request.POST.get("identity_number", ""),
            billing_address=request.POST.get("billing_address", ""),
            billing_city=request.POST.get("billing_city", ""),
            billing_country=request.POST.get("billing_country", "TR"),
            email=request.POST.get("email", ""),
            phone=request.POST.get("phone", ""),
            notes=request.POST.get("notes", ""),
            is_active=True,
            created_by=getattr(request.user, "member", None),
        )
        try:
            cari.full_clean()
        except Exception as exc:
            messages.error(request, _g("Invalid data: %(error)s") % {"error": exc})
            return redirect("current_account:cari_create")

        cari.save()

        # If opening balance non-zero, drop a single opening movement
        if cari.opening_balance and cari.opening_balance != Decimal("0"):
            CariMovement.objects.create(
                cari=cari,
                book=cari.book,
                date=cari.opening_balance_date or timezone.now().date(),
                amount=cari.opening_balance,
                currency=cari.default_currency,
                movement_type="opening",
                description="Opening balance",
                created_by=getattr(request.user, "member", None),
            )

        messages.success(request, _g("Account created: %(code)s") % {"code": cari.code})
        return redirect("current_account:cari_detail", pk=cari.pk)


@method_decorator(login_required, name="dispatch")
class CariEdit(View):
    template_name = "current_account/cari_form.html"

    def get(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        return render(request, self.template_name, {
            "cari": cari,
            "books": _books(),
            "currencies": _currencies(),
            "type_choices": CariAccount.TYPE_CHOICES,
        })

    def post(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)

        cari.name = request.POST.get("name", cari.name).strip()
        cari.type = request.POST.get("type", cari.type)
        cari.payment_term_days = int(request.POST.get("payment_term_days") or cari.payment_term_days)
        cari.credit_limit = Decimal(request.POST.get("credit_limit") or "0")
        cari.discount_rate = Decimal(request.POST.get("discount_rate") or "0")
        cari.tax_office = request.POST.get("tax_office", "")
        cari.tax_number = request.POST.get("tax_number", "")
        cari.identity_number = request.POST.get("identity_number", "")
        cari.billing_address = request.POST.get("billing_address", "")
        cari.billing_city = request.POST.get("billing_city", "")
        cari.billing_country = request.POST.get("billing_country", "TR")
        cari.email = request.POST.get("email", "")
        cari.phone = request.POST.get("phone", "")
        cari.notes = request.POST.get("notes", "")
        cari.is_active = request.POST.get("is_active") == "on"

        currency_id = request.POST.get("default_currency")
        if currency_id and str(cari.default_currency_id) != str(currency_id):
            cari.default_currency_id = int(currency_id)

        cari.save()
        messages.success(request, _g("Account updated."))
        return redirect("current_account:cari_detail", pk=cari.pk)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariDetail(View):
    template_name = "current_account/cari_detail.html"

    def get(self, request, pk):
        cari = get_object_or_404(
            CariAccount.objects.select_related("book", "default_currency",
                                               "contact", "company", "supplier"),
            pk=pk,
        )
        recent_movements = (
            cari.movements
            .select_related("currency")
            .order_by("-date", "-id")[:20]
        )
        movements_with_balance = []
        running = cari.cached_balance
        for mv in recent_movements:
            movements_with_balance.append({"mv": mv, "balance_after": running})
            running -= mv.amount

        recent_invoices = cari.invoices.select_related("currency").order_by("-date", "-id")[:10]

        ctx = {
            "cari":     cari,
            "movements": movements_with_balance,
            "recent_invoices": recent_invoices,
            "movement_type_choices": CariMovement.MOVEMENT_TYPES,
            "currencies": _currencies(),
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Statement (Ekstre)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariStatement(View):
    template_name = "current_account/cari_statement.html"

    def get(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)

        qs = cari.movements.select_related("currency").all().order_by("date", "id")
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or ""
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Walking forward → running balance per row
        running = Decimal("0.00")
        rows = []
        # Determine the opening balance (movements outside the range)
        prior_qs = cari.movements
        if date_from:
            prior_qs = prior_qs.filter(date__lt=date_from)
        else:
            prior_qs = prior_qs.none()
        running = prior_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        opening = running

        debit_total = Decimal("0.00")
        credit_total = Decimal("0.00")
        for mv in qs:
            running += mv.amount
            if mv.amount > 0:
                debit_total += mv.amount
            else:
                credit_total += abs(mv.amount)
            rows.append({"mv": mv, "balance_after": running})

        ctx = {
            "cari":         cari,
            "rows":         rows,
            "opening":      opening,
            "closing":      running,
            "debit_total":  debit_total,
            "credit_total": credit_total,
            "date_from":    date_from,
            "date_to":      date_to,
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Manual movement (used until Invoice/Payment phases land)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariMovementCreate(View):
    template_name = "current_account/movement_form.html"

    def get(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        return render(request, self.template_name, {
            "cari": cari,
            "movement_type_choices": CariMovement.MOVEMENT_TYPES,
            "currencies": _currencies(),
        })

    def post(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)

        try:
            amount = Decimal(request.POST.get("amount") or "0")
        except Exception:
            messages.error(request, _g("Invalid amount."))
            return redirect("current_account:movement_create", pk=cari.pk)

        if amount == 0:
            messages.error(request, _g("Amount cannot be zero."))
            return redirect("current_account:movement_create", pk=cari.pk)

        # User picks "direction" — debit/credit — separately from absolute amount
        direction = request.POST.get("direction") or "debit"
        signed = abs(amount) if direction == "debit" else -abs(amount)

        currency_id = request.POST.get("currency") or cari.default_currency_id
        movement_type = request.POST.get("movement_type") or "adjustment"

        mv = CariMovement.objects.create(
            cari=cari,
            book=cari.book,
            date=request.POST.get("date") or timezone.now().date(),
            due_date=request.POST.get("due_date") or None,
            amount=signed,
            currency_id=int(currency_id),
            movement_type=movement_type,
            description=request.POST.get("description", ""),
            reference=request.POST.get("reference", ""),
            created_by=getattr(request.user, "member", None),
        )
        messages.success(request, _g("Movement added."))
        return redirect("current_account:cari_detail", pk=cari.pk)


# ---------------------------------------------------------------------------
# Delete (soft — flips is_active=False; hard delete only if no movements)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariDelete(View):
    def post(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        if cari.movements.exists():
            cari.is_active = False
            cari.save(update_fields=["is_active"])
            messages.info(request, _g("Account %(code)s was deactivated (not deleted because it has movements).") % {"code": cari.code})
        else:
            code = cari.code
            cari.delete()
            messages.success(request, _g("Account %(code)s deleted.") % {"code": code})
        return redirect("current_account:cari_list")
