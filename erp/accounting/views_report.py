"""
Current-account reports (Phase 4).

    /accounting/accounts/reports/                → ReportIndex (landing page)
    /accounting/accounts/reports/trial-balance/  → TrialBalance    (current account mizan per book, period filter)
    /accounting/accounts/reports/credit-limit/   → CreditLimitReport
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from accounting.models import Book
from .models import CurrentAccount, CurrentAccountMovement


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class ReportIndex(View):
    template_name = "accounts/report_index.html"

    def get(self, request):
        over_limit_count = (
            CurrentAccount.objects
            .filter(is_active=True, credit_limit__gt=0)
            .extra(where=["cached_balance > credit_limit"])
            .count()
        )

        return render(request, self.template_name, {
            "over_limit_count":   over_limit_count,
        })


# ---------------------------------------------------------------------------
# 2. Trial Balance — Current account Mizan
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class TrialBalance(View):
    template_name = "accounts/report_trial_balance.html"

    def get(self, request):
        today = timezone.now().date()
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or today.isoformat()
        book_id   = str(request.book.pk)
        zero_filter = request.GET.get("zero") or "hide"   # show | hide

        if not date_from:
            # Default: start of current year
            date_from = today.replace(month=1, day=1).isoformat()

        # Get all current accounts (filtered by book if specified)
        current_account_qs = CurrentAccount.objects.select_related("book", "default_currency").filter(is_active=True)
        if book_id.isdigit():
            current_account_qs = current_account_qs.filter(book_id=int(book_id))

        # Per-current account aggregations
        # opening = sum movements before date_from
        # debits  = sum positive movements in [date_from, date_to]
        # credits = sum negative movements in [date_from, date_to]
        # closing = opening + debits + credits
        # One grouped aggregate for every account, not three per account in
        # a Python loop. Laleli has 1,277 active accounts, so the loop was
        # 3,831 round trips to a database at the end of a proxy connection
        # and the page took minutes to answer. The same three figures fall
        # out of a single query with filtered aggregates.
        #
        # amount_base, not amount. `amount` is what was ENTERED, in
        # whatever currency the movement was written in, and this page adds
        # those together: 877 dollar movements, 16 lira and 2 euro on
        # Laleli, six accounts holding more than one currency, all summed
        # as though a lira were a dollar. The grand total read 302,676.10
        # against a real position of 349,327.22 — understated by 46,651.12
        # by an addition that was never meaningful. amount_base is what
        # cached_balance and the balance sheet already use, so the mizan
        # now agrees with the account pages instead of quietly contradicting
        # them. Every figure on the page is the book's base currency, which
        # the header now says out loud.
        ZERO = Decimal("0.00")
        totals = {
            r["current_account_id"]: r
            for r in (CurrentAccountMovement.objects
                      .filter(current_account__in=current_account_qs, date__lte=date_to)
                      .values("current_account_id")
                      .annotate(
                          opening=Sum("amount_base", filter=Q(date__lt=date_from)),
                          debits=Sum("amount_base", filter=Q(date__gte=date_from,
                                                             amount_base__gt=0)),
                          credits=Sum("amount_base", filter=Q(date__gte=date_from,
                                                              amount_base__lt=0)),
                      ))
        }

        rows = []
        for current_account in current_account_qs:
            # An account with no movements at all is absent from the
            # aggregate rather than present with zeros.
            t = totals.get(current_account.pk)
            opening = (t["opening"] if t and t["opening"] is not None else ZERO)
            debits = (t["debits"] if t and t["debits"] is not None else ZERO)
            credits = (t["credits"] if t and t["credits"] is not None else ZERO)
            closing = opening + debits + credits

            if zero_filter == "hide" and opening == 0 and debits == 0 and credits == 0:
                continue

            rows.append({
                "current_account":    current_account,
                "opening": opening,
                "debits":  debits,
                "credits": abs(credits),
                "closing": closing,
            })

        rows.sort(key=lambda r: r["current_account"].code)

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
            "base_currency": getattr(request.book, "base_currency", None),
            "zero_filter": zero_filter,
            "books": Book.objects.all().order_by("name"),
        })


# ---------------------------------------------------------------------------
# 3. Credit Limit Report — Risk Limiti
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CreditLimitReport(View):
    template_name = "accounts/report_credit_limit.html"

    def get(self, request):
        book_id = str(request.book.pk)
        view = request.GET.get("view") or "over"  # over | near | all

        qs = (CurrentAccount.objects
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
                "current_account": c,
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


@method_decorator(login_required, name="dispatch")
class BalanceSheet(View):
    """Assets = Liabilities + Equity, twice over.

    The left column is the general ledger, where the equation is true by
    construction because an unbalanced entry cannot be written. The right
    column is the same equation computed from the subsidiary ledgers, the
    way it has always had to be computed — and there it does not balance,
    by $353,865.03 on Laleli and $1,319,947.21 on Ergene.

    Both are shown because the ledger starts empty and fills up as history
    is backfilled. Everything that happens from now on posts as it happens
    — see signals_ledger — so the gap between the columns is the past, not
    the present, and it stops growing. Watching them converge IS the
    migration; when they agree, it is finished. Showing only the ledger
    would report a tidy zero while the money sat somewhere else entirely.
    """
    template_name = "accounts/report_balance_sheet.html"

    def get(self, request):
        from .services_ledger import (balance_sheet, reconcile,
                                       subsidiary_equation)

        date_to = request.GET.get("date_to") or None
        gl = balance_sheet(request.book, date_to=date_to)
        subs = subsidiary_equation(request.book)
        # What each control account says against the ledger it summarises.
        # The two columns above say whether the ledger has caught up; this
        # says WHERE it has not, which is the difference between a number to
        # worry about and a job to do.
        rec = reconcile(request.book, date_to=date_to)

        # How far the ledger has come. Zero when nothing is posted yet; 100
        # when the two agree on total assets.
        coverage = None
        if subs["assets"]:
            coverage = (gl["assets"] / subs["assets"] * 100).quantize(
                Decimal("0.1"))

        return render(request, self.template_name, {
            "gl": gl,
            "subs": subs,
            "rec": rec,
            "coverage": coverage,
            "date_to": date_to or "",
            "identity_holds": subs["causes_total"] == subs["residual"],
        })
