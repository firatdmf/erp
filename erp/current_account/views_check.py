"""
Check / Promissory Note views (Phase 5).

    /cari/cek-senet/                       → CheckList
    /cari/cek-senet/yeni/                  → CheckCreate
    /cari/cek-senet/yeni/?cari=<id>        → CheckCreate prefilled
    /cari/cek-senet/<id>/                  → CheckDetail
    /cari/cek-senet/<id>/ciro/             → CheckEndorse  (received only)
    /cari/cek-senet/<id>/bankaya-ver/      → CheckDeposit  (received only)
    /cari/cek-senet/<id>/tahsil/           → CheckClear
    /cari/cek-senet/<id>/karsiliksiz/      → CheckBounce   (received only)
    /cari/cek-senet/<id>/iptal/            → CheckCancel
    /cari/cek-senet/<id>/sil/              → CheckDelete (only if status=cancelled and no movements)
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import CashAccount, CurrencyCategory
from .models import CariAccount, CheckOrPromissoryNote


def _D(val, default="0"):
    try:
        return Decimal(str(val if val not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _filter_checks(request):
    qs = (CheckOrPromissoryNote.objects
          .select_related("cari", "book", "currency", "endorsed_to")
          .all())

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(serial_no__icontains=q)
            | Q(bank__icontains=q)
            | Q(drawer__icontains=q)
            | Q(cari__name__icontains=q)
            | Q(cari__code__icontains=q)
        )

    cari_id = request.GET.get("cari") or ""
    if cari_id.isdigit():
        qs = qs.filter(cari_id=int(cari_id))

    instr = request.GET.get("instrument") or ""
    if instr in dict(CheckOrPromissoryNote.INSTRUMENT_TYPES):
        qs = qs.filter(instrument=instr)

    direction = request.GET.get("direction") or ""
    if direction in dict(CheckOrPromissoryNote.DIRECTION_CHOICES):
        qs = qs.filter(direction=direction)

    status = request.GET.get("status") or ""
    if status in dict(CheckOrPromissoryNote.STATUS_CHOICES):
        qs = qs.filter(status=status)

    return qs.order_by("due_date", "id")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CheckList(View):
    template_name = "current_account/check_list.html"

    def get(self, request):
        qs = _filter_checks(request)

        # Stats: portfolio totals by direction
        portfolio_received = qs.filter(direction="received", status="portfolio").aggregate(s=Sum("amount"))["s"] or Decimal("0")
        portfolio_given    = qs.filter(direction="given",    status="portfolio").aggregate(s=Sum("amount"))["s"] or Decimal("0")
        overdue_count = qs.filter(status="portfolio", due_date__lt=timezone.now().date()).count()

        return render(request, self.template_name, {
            "checks": qs[:500],
            "n": qs.count(),
            "portfolio_received": portfolio_received,
            "portfolio_given":    portfolio_given,
            "overdue_count":      overdue_count,
            "instrument_choices": CheckOrPromissoryNote.INSTRUMENT_TYPES,
            "direction_choices":  CheckOrPromissoryNote.DIRECTION_CHOICES,
            "status_choices":     CheckOrPromissoryNote.STATUS_CHOICES,
            "q":             request.GET.get("q", ""),
            "filter_instrument": request.GET.get("instrument", ""),
            "filter_direction":  request.GET.get("direction", ""),
            "filter_status":     request.GET.get("status", ""),
        })


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CheckCreate(View):
    template_name = "current_account/check_form.html"

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
            "check": None,
            "prefilled_cari": prefilled_cari,
            "cari_options": cari_options,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "instrument_choices": CheckOrPromissoryNote.INSTRUMENT_TYPES,
            "direction_choices":  CheckOrPromissoryNote.DIRECTION_CHOICES,
        })

    def post(self, request):
        cari_id = request.POST.get("cari")
        if not cari_id:
            messages.error(request, _g("An account must be selected."))
            return redirect("current_account:check_create")
        cari = get_object_or_404(CariAccount, pk=int(cari_id))

        amount = _D(request.POST.get("amount"))
        if amount <= 0:
            messages.error(request, _g("Amount must be greater than zero."))
            return redirect("current_account:check_create")

        try:
            check = CheckOrPromissoryNote.objects.create(
                book=cari.book,
                cari=cari,
                instrument=request.POST.get("instrument") or "check",
                direction=request.POST.get("direction") or "received",
                serial_no=request.POST.get("serial_no", "").strip()[:50],
                bank=request.POST.get("bank", "")[:100],
                branch=request.POST.get("branch", "")[:100],
                account_no=request.POST.get("account_no", "")[:50],
                drawer=request.POST.get("drawer", "")[:200],
                amount=amount,
                currency_id=int(request.POST.get("currency") or cari.default_currency_id),
                issue_date=request.POST.get("issue_date") or timezone.now().date(),
                due_date=request.POST.get("due_date") or timezone.now().date(),
                notes=request.POST.get("notes", ""),
                created_by=getattr(request.user, "member", None),
            )
        except ValidationError as ve:
            messages.error(request, _g("Invalid data: %(error)s") % {"error": ve})
            return redirect("current_account:check_create")

        messages.success(request, _g("%(instrument)s added to portfolio: #%(serial)s") % {"instrument": check.get_instrument_display(), "serial": check.serial_no})
        return redirect("current_account:check_detail", pk=check.pk)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CheckDetail(View):
    template_name = "current_account/check_detail.html"

    def get(self, request, pk):
        check = get_object_or_404(
            CheckOrPromissoryNote.objects.select_related(
                "cari", "book", "currency", "endorsed_to",
                "posted_movement", "endorse_movement", "cleared_cash_account",
            ),
            pk=pk,
        )

        # Cash accounts in the same book (for clear action)
        cash_accounts = CashAccount.objects.filter(book=check.book).order_by("name")
        # Other caris for endorsement target
        other_caris = (CariAccount.objects.filter(book=check.book, is_active=True)
                       .exclude(pk=check.cari_id).order_by("name"))

        return render(request, self.template_name, {
            "check": check,
            "cash_accounts": cash_accounts,
            "other_caris": other_caris,
            "today": timezone.now().date(),
        })


# ---------------------------------------------------------------------------
# State transition actions
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CheckEndorse(View):
    def post(self, request, pk):
        check = get_object_or_404(CheckOrPromissoryNote, pk=pk)
        target_id = request.POST.get("endorsed_to")
        if not target_id:
            messages.error(request, _g("An account to endorse to must be selected."))
            return redirect("current_account:check_detail", pk=pk)
        target = get_object_or_404(CariAccount, pk=int(target_id))
        try:
            check.endorse(to_cari=target, user=request.user)
            messages.success(request, _g("Check endorsed to %(name)s.") % {"name": target.name})
        except ValidationError as ve:
            messages.error(request, _g("Endorsement failed: %(error)s") % {"error": ve})
        return redirect("current_account:check_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class CheckDeposit(View):
    def post(self, request, pk):
        check = get_object_or_404(CheckOrPromissoryNote, pk=pk)
        try:
            check.deposit(user=request.user)
            messages.success(request, _g("Check marked as deposited to bank."))
        except ValidationError as ve:
            messages.error(request, _g("Operation failed: %(error)s") % {"error": ve})
        return redirect("current_account:check_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class CheckClear(View):
    def post(self, request, pk):
        check = get_object_or_404(CheckOrPromissoryNote, pk=pk)
        cash_id = request.POST.get("cash_account")
        if not cash_id:
            messages.error(request, _g("A cash account must be selected."))
            return redirect("current_account:check_detail", pk=pk)
        cash = get_object_or_404(CashAccount, pk=int(cash_id))
        try:
            check.clear(cash_account=cash, user=request.user)
            messages.success(request, _g("Check cleared: %(name)s") % {"name": cash.name})
        except ValidationError as ve:
            messages.error(request, _g("Could not clear: %(error)s") % {"error": ve})
        return redirect("current_account:check_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class CheckBounce(View):
    def post(self, request, pk):
        check = get_object_or_404(CheckOrPromissoryNote, pk=pk)
        reason = request.POST.get("reason", "")
        try:
            check.bounce(user=request.user, reason=reason)
            messages.success(request, _g("Check marked as bounced."))
        except ValidationError as ve:
            messages.error(request, _g("Operation failed: %(error)s") % {"error": ve})
        return redirect("current_account:check_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class CheckCancel(View):
    def post(self, request, pk):
        check = get_object_or_404(CheckOrPromissoryNote, pk=pk)
        reason = request.POST.get("reason", "")
        check.cancel(user=request.user, reason=reason)
        messages.success(request, _g("Check cancelled."))
        return redirect("current_account:check_detail", pk=pk)
