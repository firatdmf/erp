"""
Reports for current_account (Phase 4).

    /cari/rapor/                       → ReportIndex (landing page with 4 cards)
    /cari/rapor/yaslandirma/           → AgingReport     (aged receivables/payables)
    /cari/rapor/mizan/                 → TrialBalance    (cari mizan per book, period filter)
    /cari/rapor/risk-limiti/           → CreditLimitReport
    /cari/rapor/vade-takvimi/          → DueCalendar     (upcoming + overdue invoice due dates)
"""
from datetime import date as date_cls, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import Book
from .models import CariAccount, CariMovement, Invoice


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class ReportIndex(View):
    template_name = "current_account/report_index.html"

    def get(self, request):
        today = timezone.now().date()
        overdue_count = Invoice.objects.filter(
            status__in=["issued", "partially_paid", "overdue"],
            balance__gt=0,
            due_date__lt=today,
        ).count()

        over_limit_count = (
            CariAccount.objects
            .filter(is_active=True, credit_limit__gt=0)
            .extra(where=["cached_balance > credit_limit"])
            .count()
        )

        upcoming_due_count = Invoice.objects.filter(
            status__in=["issued", "partially_paid"],
            balance__gt=0,
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
        ).count()

        return render(request, self.template_name, {
            "overdue_count":      overdue_count,
            "over_limit_count":   over_limit_count,
            "upcoming_due_count": upcoming_due_count,
        })


# ---------------------------------------------------------------------------
# 1. Aging Report — Yaşlandırma
# ---------------------------------------------------------------------------
BUCKETS = [
    ("not_due",    _("Not Due"),     None, 0),    # due_date >= today
    ("b_0_30",     _("0-30 Days"),   0,    30),
    ("b_30_60",    _("30-60 Days"),  30,   60),
    ("b_60_90",    _("60-90 Days"),  60,   90),
    ("b_90_plus",  _("90+ Days"),    90,   None),
]


@method_decorator(login_required, name="dispatch")
class AgingReport(View):
    template_name = "current_account/report_aging.html"

    def get(self, request):
        today = timezone.now().date()

        book_id = request.GET.get("book") or ""
        kind = request.GET.get("kind") or "receivable"   # receivable | payable

        # Open invoices with balance > 0, not draft/cancelled
        qs = (Invoice.objects
              .filter(balance__gt=0, status__in=["issued", "partially_paid", "overdue"])
              .select_related("cari", "currency", "book"))

        if kind == "receivable":
            qs = qs.filter(type__in=["sales", "purchase_return"])
        else:
            qs = qs.filter(type__in=["purchase", "sales_return"])

        if book_id.isdigit():
            qs = qs.filter(book_id=int(book_id))

        # Group: cari → buckets
        per_cari = {}
        for inv in qs.order_by("cari__code", "due_date"):
            row = per_cari.setdefault(inv.cari_id, {
                "cari": inv.cari,
                "currency": inv.currency.code,
                "buckets": {k: Decimal("0") for k, *_ in BUCKETS},
                "total": Decimal("0"),
                "oldest_invoice": None,
                "max_days_overdue": 0,
            })

            days = (today - inv.due_date).days
            if inv.due_date >= today:
                bucket = "not_due"
            elif days <= 30:
                bucket = "b_0_30"
            elif days <= 60:
                bucket = "b_30_60"
            elif days <= 90:
                bucket = "b_60_90"
            else:
                bucket = "b_90_plus"

            row["buckets"][bucket] += inv.balance
            row["total"] += inv.balance
            if row["oldest_invoice"] is None or inv.date < row["oldest_invoice"].date:
                row["oldest_invoice"] = inv
            if days > row["max_days_overdue"]:
                row["max_days_overdue"] = days

        rows = sorted(per_cari.values(), key=lambda r: -r["total"])

        # Grand totals per bucket
        grand_buckets = {k: Decimal("0") for k, *_ in BUCKETS}
        grand_total = Decimal("0")
        for r in rows:
            for k in grand_buckets:
                grand_buckets[k] += r["buckets"][k]
            grand_total += r["total"]

        return render(request, self.template_name, {
            "today": today,
            "rows": rows,
            "buckets": BUCKETS,
            "grand_buckets": grand_buckets,
            "grand_total": grand_total,
            "kind": kind,
            "filter_book": book_id,
            "books": Book.objects.all().order_by("name"),
        })


# ---------------------------------------------------------------------------
# 2. Trial Balance — Cari Mizan
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class TrialBalance(View):
    template_name = "current_account/report_trial_balance.html"

    def get(self, request):
        today = timezone.now().date()
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or today.isoformat()
        book_id   = request.GET.get("book") or ""
        zero_filter = request.GET.get("zero") or "hide"   # show | hide

        if not date_from:
            # Default: start of current year
            date_from = today.replace(month=1, day=1).isoformat()

        # Get all caris (filtered by book if specified)
        cari_qs = CariAccount.objects.select_related("book", "default_currency").filter(is_active=True)
        if book_id.isdigit():
            cari_qs = cari_qs.filter(book_id=int(book_id))

        # Per-cari aggregations
        # opening = sum movements before date_from
        # debits  = sum positive movements in [date_from, date_to]
        # credits = sum negative movements in [date_from, date_to]
        # closing = opening + debits + credits
        rows = []
        for cari in cari_qs:
            mvs = cari.movements.filter(date__lte=date_to)
            opening = (mvs.filter(date__lt=date_from).aggregate(s=Sum("amount"))["s"]
                       or Decimal("0.00"))
            in_period = mvs.filter(date__gte=date_from)
            debits  = in_period.filter(amount__gt=0).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
            credits = in_period.filter(amount__lt=0).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
            closing = opening + debits + credits

            if zero_filter == "hide" and opening == 0 and debits == 0 and credits == 0:
                continue

            rows.append({
                "cari":    cari,
                "opening": opening,
                "debits":  debits,
                "credits": abs(credits),
                "closing": closing,
            })

        rows.sort(key=lambda r: r["cari"].code)

        # Grand totals
        g_opening = sum((r["opening"] for r in rows), Decimal("0.00"))
        g_debits  = sum((r["debits"]  for r in rows), Decimal("0.00"))
        g_credits = sum((r["credits"] for r in rows), Decimal("0.00"))
        g_closing = sum((r["closing"] for r in rows), Decimal("0.00"))

        return render(request, self.template_name, {
            "rows": rows,
            "g_opening": g_opening,
            "g_debits": g_debits,
            "g_credits": g_credits,
            "g_closing": g_closing,
            "date_from": date_from,
            "date_to": date_to,
            "filter_book": book_id,
            "zero_filter": zero_filter,
            "books": Book.objects.all().order_by("name"),
        })


# ---------------------------------------------------------------------------
# 3. Credit Limit Report — Risk Limiti
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CreditLimitReport(View):
    template_name = "current_account/report_credit_limit.html"

    def get(self, request):
        book_id = request.GET.get("book") or ""
        view = request.GET.get("view") or "over"  # over | near | all

        qs = (CariAccount.objects
              .select_related("book", "default_currency")
              .filter(is_active=True, credit_limit__gt=0))

        if book_id.isdigit():
            qs = qs.filter(book_id=int(book_id))

        rows = []
        for c in qs:
            if c.credit_limit <= 0:
                continue
            usage_pct = (c.cached_balance / c.credit_limit * 100) if c.credit_limit else Decimal("0")
            available = c.credit_limit - c.cached_balance

            row = {
                "cari": c,
                "balance": c.cached_balance,
                "credit_limit": c.credit_limit,
                "usage_pct": usage_pct,
                "available": available,
                "is_over": c.cached_balance > c.credit_limit,
                "is_near": usage_pct >= 80 and c.cached_balance <= c.credit_limit,
            }

            if view == "over" and not row["is_over"]:
                continue
            if view == "near" and not (row["is_near"] or row["is_over"]):
                continue
            rows.append(row)

        rows.sort(key=lambda r: -r["usage_pct"])

        return render(request, self.template_name, {
            "rows": rows,
            "view": view,
            "filter_book": book_id,
            "books": Book.objects.all().order_by("name"),
        })


# ---------------------------------------------------------------------------
# 4. Due Calendar — Vade Takvimi
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class DueCalendar(View):
    template_name = "current_account/report_due_calendar.html"

    def get(self, request):
        today = timezone.now().date()
        book_id = request.GET.get("book") or ""
        kind = request.GET.get("kind") or "receivable"

        qs = (Invoice.objects
              .filter(balance__gt=0, status__in=["issued", "partially_paid", "overdue"])
              .select_related("cari", "currency"))
        if kind == "receivable":
            qs = qs.filter(type__in=["sales", "purchase_return"])
        else:
            qs = qs.filter(type__in=["purchase", "sales_return"])
        if book_id.isdigit():
            qs = qs.filter(book_id=int(book_id))

        # Buckets
        end_of_this_week = today + timedelta(days=(6 - today.weekday()))
        end_of_next_week = end_of_this_week + timedelta(days=7)
        end_of_month     = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        groups = {
            "overdue":      {"label": _("Overdue"),         "items": [], "total": Decimal("0")},
            "this_week":    {"label": _("This Week"),       "items": [], "total": Decimal("0")},
            "next_week":    {"label": _("Next Week"),       "items": [], "total": Decimal("0")},
            "this_month":   {"label": _("This Month (end)"),"items": [], "total": Decimal("0")},
            "later":        {"label": _("Later"),           "items": [], "total": Decimal("0")},
        }

        for inv in qs.order_by("due_date"):
            d = inv.due_date
            if d < today:
                key = "overdue"
            elif d <= end_of_this_week:
                key = "this_week"
            elif d <= end_of_next_week:
                key = "next_week"
            elif d <= end_of_month:
                key = "this_month"
            else:
                key = "later"
            groups[key]["items"].append({
                "inv": inv,
                "days_diff": (d - today).days,
            })
            groups[key]["total"] += inv.balance

        return render(request, self.template_name, {
            "today": today,
            "groups": groups,
            "kind": kind,
            "filter_book": book_id,
            "books": Book.objects.all().order_by("name"),
        })
