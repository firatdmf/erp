from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseRedirect

# from django.views.generic import TemplateView
from django.urls import reverse_lazy, reverse
from django.views import View, generic
from django.db import transaction, IntegrityError, DatabaseError, OperationalError

# from operating.models import Product

from .models import *

# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import *
from django.forms import modelformset_factory
from datetime import datetime
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _g


from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum, Count, Window, Case, When, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import decimal
import json

# import yfinance as yf
from decimal import Decimal, ROUND_HALF_UP
import math
import time
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.contenttypes.models import ContentType

# add functions here


def get_total_base_currency_balance(book_pk):
    # The book's own reporting currency, not the deployment's — two books
    # need not keep their accounts in the same one.
    book = Book.objects.filter(pk=book_pk).first()
    base_currency = book.effective_base_currency if book else get_base_currency()
    total = Decimal("0.00")

    for currency_category in CurrencyCategory.objects.all():
        # sum all accounts of this currency
        cash_accounts = CashAccount.objects.filter(
            book=book_pk,
            currency=currency_category,
        )
        balance = sum(ca.balance for ca in cash_accounts)

        if balance == 0:
            continue

        if currency_category != base_currency:
            from .services import get_exchange_rate

            rate = get_exchange_rate(currency_category.code, base_currency.code)
            if not rate:
                raise ValidationError(
                    {
                        "currency_rate": f"Failed to get rate {currency_category.code} → {base_currency.code}"
                    }
                )
            balance = Decimal(balance)
            rate = Decimal(rate)

            total += (balance * rate).quantize(Decimal("0.01"))
        else:
            balance = Decimal(balance)
            total += balance

    return total


# def get_exchange_rate(self, from_currency, to_currency):
#     ticker = f"{from_currency}{to_currency}=X"
#     data = yf.Ticker(ticker)
#     exchange_rate = data.history(period="1d")["Close"][0]
#     return Decimal(exchange_rate)


@method_decorator(login_required, name="dispatch")
class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.all()
        context["books"] = books
        return context


@method_decorator(login_required, name="dispatch")
class CreateBook(generic.edit.CreateView):
    model = Book
    form_class = BookForm
    template_name = "accounting/create_book.html"

    def get_template_names(self):
        if self.request.headers.get('HX-Request') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ["accounting/partials/book_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': self.get_success_url()
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            }, status=400)
        return super().form_invalid(form)

    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.object.pk})


@method_decorator(login_required, name="dispatch")
class BookShares(View):
    """Manage a book's cap table on a page of its own.

    Holdings used to be editable in place in the book header, which was
    convenient and wrong twice over: it overwrote ownership with no
    record of who changed it or why, and it put a legally significant
    number behind a click on a summary. Changes are recorded here, as
    dated rows.
    """

    template_name = "accounting/book_shares.html"

    def get_book(self):
        return get_object_or_404(Book, pk=self.kwargs.get("pk"))

    def rows(self, book):
        pool = book.total_shares or 0
        out = []
        for sb in book.stakeholders.select_related("member__user").order_by("-shares", "pk"):
            out.append({
                "sb": sb,
                "member": sb.member,
                "shares": sb.shares,
                "pct": (
                    (Decimal(sb.shares) / Decimal(pool) * 100).quantize(Decimal("0.01"))
                    if pool else None
                ),
                "issuances": list(
                    sb.issuances.select_related("created_by__user", "capital")
                ),
            })
        return out

    def context(self, book, **extra):
        rows = self.rows(book)
        issued = sum(r["shares"] for r in rows)
        pool = book.total_shares or 0
        context = {
            "book": book,
            "rows": rows,
            "shares_issued": issued,
            "shares_pool": pool,
            "shares_unissued": max(pool - issued, 0),
            "reasons": ShareIssuance.REASONS,
            "today": timezone.now().date().isoformat(),
            # Offered so an issuance can name the money that bought it.
            # Optional: most movements are transfers or corrections and
            # have no contribution behind them at all.
            "capital_entries": (
                EquityCapital.objects.filter(book=book)
                .select_related("currency", "member__user")
                .order_by("-date_invested", "-id")
            ),
        }
        context.update(extra)
        return context

    def get(self, request, pk):
        book = self.get_book()
        return render(request, self.template_name, self.context(book))

    def post(self, request, pk):
        book = self.get_book()
        action = request.POST.get("action")
        if action == "pool":
            return self._set_pool(request, book)
        return self._record_issuance(request, book)

    def _set_pool(self, request, book):
        raw = (request.POST.get("total_shares") or "").replace(",", "").strip()
        try:
            total = int(raw)
        except ValueError:
            return self._fail(request, book, "Enter a whole number of shares.")
        if total < 1:
            return self._fail(request, book, "A book needs at least one share.")

        issued = sum(sb.shares for sb in book.stakeholders.all())
        if total < issued:
            return self._fail(
                request, book,
                "%s shares are already allocated — the pool cannot be smaller."
                % f"{issued:,}",
            )

        book.total_shares = total
        book.save(update_fields=["total_shares"])
        messages.success(request, _g("Share pool set to %s.") % f"{total:,}")
        return redirect("accounting:book_shares", pk=book.pk)

    def _record_issuance(self, request, book):
        sb = StakeholderBook.objects.filter(
            pk=request.POST.get("stakeholder"), book=book
        ).first()
        if sb is None:
            return self._fail(request, book, "Pick a stakeholder.")

        raw = (request.POST.get("shares") or "").replace(",", "").strip()
        try:
            shares = int(raw)
        except ValueError:
            return self._fail(request, book, "Enter a whole number of shares.")
        if shares == 0:
            return self._fail(request, book, "Nothing to record — enter a non-zero number.")

        # Negative rows take shares back, so the floor is the holder's own
        # position: you cannot claw back more than they hold.
        if sb.shares + shares < 0:
            return self._fail(
                request, book,
                "%s holds %s shares — you cannot take back more than that."
                % (sb.member, f"{sb.shares:,}"),
            )
        if shares > 0:
            error = validate_share_allocation(book, sb.shares + shares, exclude_pk=sb.pk)
            if error:
                return self._fail(request, book, error)

        # A contribution from another book would tie this issuance to
        # money that never entered it.
        capital = EquityCapital.objects.filter(
            pk=request.POST.get("capital") or 0, book=book
        ).first()

        ShareIssuance.objects.create(
            stakeholder=sb,
            shares=shares,
            date=request.POST.get("date") or timezone.now().date(),
            reason=request.POST.get("reason") or "capital",
            note=(request.POST.get("note") or "").strip(),
            capital=capital,
            created_by=getattr(request.user, "member", None),
        )
        messages.success(
            request,
            _g("Recorded %(n)s shares for %(who)s.")
            % {"n": f"{shares:+,}", "who": sb.member},
        )
        return redirect("accounting:book_shares", pk=book.pk)

    def _fail(self, request, book, message):
        return render(
            request, self.template_name,
            self.context(book, error=message, form_data=request.POST),
            status=400,
        )


@method_decorator(login_required, name="dispatch")
class AddCashAccount(generic.edit.CreateView):
    """Create a cash account on a book.

    The book comes from the URL rather than a form field, so an account
    can only ever be created onto the book whose page you started from.
    """

    model = CashAccount
    form_class = CashAccountForm
    template_name = "accounting/cash_account_form.html"

    def get_book(self):
        return get_object_or_404(Book, pk=self.kwargs.get("pk"))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["book"] = self.get_book()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["book"] = self.get_book()
        return context

    def get_success_url(self):
        return reverse("accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")})


@method_decorator(login_required, name="dispatch")
class EditCashAccount(generic.edit.UpdateView):
    """Edit one of a book's cash accounts.

    Reached from the Cash Accounts card on the book detail page, and
    scoped to that book: an account belongs to exactly one book, so
    /books/3/cash_accounts/9/edit/ must 404 when account 9 lives in
    another book rather than quietly editing it.
    """

    model = CashAccount
    form_class = CashAccountForm
    template_name = "accounting/cash_account_form.html"
    pk_url_kwarg = "account_pk"
    context_object_name = "cash_account"

    def get_queryset(self):
        return CashAccount.objects.filter(
            book=self.kwargs.get("pk")
        ).select_related("book", "currency")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["book"] = self.object.book
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["book"] = self.object.book
        return context

    def get_success_url(self):
        return reverse("accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")})


@method_decorator(login_required, name="dispatch")
class RenameBook(generic.edit.UpdateView):
    """Rename a book in place from its detail page header.

    POST-only and JSON-only — the page swaps the <h1> for an input and
    posts here, so there is no GET form to render and no redirect to
    follow. Uniqueness and length come from the model field, so a
    clashing or empty name comes back as a 400 the header can show
    without leaving the page.
    """

    model = Book
    form_class = BookNameForm
    http_method_names = ["post"]

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({"success": True, "name": self.object.name})

    def form_invalid(self, form):
        return JsonResponse(
            {"success": False, "errors": form.errors.get_json_data()}, status=400
        )


class SetBookBrandName(generic.edit.UpdateView):
    """Set the name this book's documents print with.

    Same POST-only, JSON-only shape as RenameBook — the detail page
    edits the value in place. Blank is a legitimate value here (unlike
    `name`): it means "fall back to the brand default", so the response
    returns the EFFECTIVE name for the page to show.
    """

    model = Book
    form_class = BookBrandNameForm
    http_method_names = ["post"]

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            "success": True,
            "brand_name": self.object.brand_name,
            "effective": self.object.effective_brand_name,
        })

    def form_invalid(self, form):
        return JsonResponse(
            {"success": False, "errors": form.errors.get_json_data()}, status=400
        )


class SetDefaultCariTarget(generic.detail.SingleObjectMixin, generic.View):
    """Make this book the one the current-account ledger posts to.

    POST-only and JSON-only, like the other header editors. Not a
    ModelForm: the flag is unique across books, so setting it here has
    to clear it there, which is Book.make_default_cari_target's job rather than
    a per-row form's.

    Turning the flag OFF is deliberately not offered. "No book is the
    ledger" sends get_default_book() back to guessing by account count,
    which is the failure this replaced — you move the ledger to another
    book, you do not unset it.
    """

    model = Book
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        book = self.get_object()
        book.make_default_cari_target()
        return JsonResponse({"success": True, "book": book.pk, "name": book.name})


@method_decorator(login_required, name="dispatch")
class SetMyWorkingBook(generic.detail.SingleObjectMixin, generic.View):
    """Make this the book the logged-in member's work is booked into.

    Per member, not per app: several businesses run on one install and
    which one a record belongs to follows the person entering it. Unlike
    the app-level default, this one CAN be cleared — a member who works
    across businesses falls back to the app default, which is a
    legitimate way to work rather than a broken state.
    """

    model = Book
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        book = self.get_object()
        member = getattr(request.user, "member", None)
        if member is None:
            return JsonResponse(
                {"success": False, "error": "No member profile."}, status=400)
        clearing = request.POST.get("clear") == "1"
        member.default_book = None if clearing else book
        member.save(update_fields=["default_book"])
        return JsonResponse({
            "success": True,
            "book": None if clearing else book.pk,
            "name": None if clearing else book.name,
        })


@method_decorator(login_required, name="dispatch")
class WorkingBookRedirect(generic.RedirectView):
    """Send a book-scoped view the member's working book.

    The sidebar is built from erp/nav.py, a module-level list with no
    request behind it, so `{% url it.url %}` can take no arguments. Every
    action moved off the book page needs a book id, so the menu points
    here instead and the book is resolved per request from
    Member.default_book — the same "working book" the book page's own
    toggle sets.

    A member who has not picked one lands on the ledger index rather than
    a 404 or somebody else's book: choosing the book is the step they are
    missing, so send them where that choice is made.
    """
    permanent = False
    target = None

    def get_redirect_url(self, *args, **kwargs):
        member = getattr(self.request.user, "member", None)
        book = getattr(member, "default_book", None)
        if not book:
            return reverse("accounting:index")
        return reverse(self.target, args=[book.pk])


def _sum_in_base(model, book, field):
    """Total `field` across a book's rows, each converted at its own rate.

    These tables carry a currency FK per row, so a plain Sum() adds TRY to
    USD and returns a number that is not money — the same trap
    CariMovement.amount_base exists to avoid. Book 2's three capital rows
    are one USD, one EUR and one TRY, so the naive total was wrong by
    whatever the non-USD pair happened to be worth.

    A row whose currency has no published rate is skipped rather than
    guessed at, and the caller shows the equation as unbalanced — which is
    the truthful outcome, since the money really is unaccounted for.
    """
    from .services import get_exchange_rate

    base = get_base_currency()
    total = Decimal("0.00")

    for row in model.objects.filter(book=book).select_related("currency"):
        amount = getattr(row, field) or Decimal("0.00")
        if not amount:
            continue
        if row.currency_id == base.pk:
            total += Decimal(amount)
            continue
        rate = get_exchange_rate(row.currency.code, base.code)
        if not rate:
            continue
        total += (Decimal(amount) * Decimal(rate)).quantize(Decimal("0.01"))

    return total


@method_decorator(login_required, name="dispatch")
class BookDetail(generic.DetailView):
    model = Book
    template_name = "accounting/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        # Is this the logged-in member's own working book? Drives the
        # header toggle — per member, so it cannot be read off the row.
        member = getattr(self.request.user, "member", None)
        context["is_my_working_book"] = bool(
            member and member.default_book_id == book.pk)
        context["my_working_book"] = getattr(member, "default_book", None)
        context["cash_accounts"] = (
            CashAccount.objects.filter(book=book)
            .select_related("currency")
            .order_by("currency__code", "name")
        )

        # Who owes the book money and who it owes, read off the cari cards
        # rather than the AR/AP mirror tables the block above still holds.
        # Those mirrors are written per-movement by signals_accounts and
        # skip the movement types _mirror_to_legacy has no side for, so the
        # payable table lists ten rows against three hundred real ones.
        # Showing them would contradict the equation directly above, which
        # is built from the netted cached_balance.
        cari_qs = CariAccount.objects.filter(book=book)
        context["top_receivables"] = (
            cari_qs.filter(cached_balance__gt=0)
            .order_by("-cached_balance")[:10]
        )
        context["top_payables"] = (
            cari_qs.filter(cached_balance__lt=0)
            .order_by("cached_balance")[:10]
        )
        context["receivable_count"] = cari_qs.filter(cached_balance__gt=0).count()
        context["payable_count"] = cari_qs.filter(cached_balance__lt=0).count()

        # Stakeholders, with the stake each one's shares actually buy.
        # Book.total_shares is the pool every holding is measured against
        # ("used to calculate stake of each owner based on their shares"),
        # so an unissued book leaves everyone at 0% rather than dividing
        # by nothing.
        pool = book.total_shares or 0
        context["stakeholders"] = [
            {
                "pk": sb.pk,
                "member": sb.member,
                "shares": sb.shares,
                "pct": (
                    (Decimal(sb.shares) / Decimal(pool) * 100).quantize(Decimal("0.1"))
                    if pool
                    else None
                ),
            }
            for sb in book.stakeholders.select_related("member__user").order_by(
                "-shares", "pk"
            )
        ]
        context["shares_pool"] = pool
        context["shares_issued"] = sum(sb.shares for sb in book.stakeholders.all())

        context.update(self._accounting_equation(book))

        return context

    # ------------------------------------------------------------------
    @staticmethod
    def _accounting_equation(book):
        """Assets = Liabilities + Equity, as far as the data supports it.

        Receivables and payables are read off CariAccount.cached_balance,
        which is now the only place they live. They were also mirrored into
        AssetAccountsReceivable / LiabilityAccountsPayable tables, which
        this function pointedly did not sum: those mirrors were written per
        movement and never netted, and a payable was skipped outright
        unless the account carried a supplier FK, so the payable table held
        ten rows where the ledger had three hundred. Summing them reported
        a position off by six figures. The tables are gone; cached_balance
        is the netted figure the rest of the app already trusts, and it
        reconciles to the Excel export to the cent.

        The equation will NOT balance, and that is a property of the data
        rather than of this function. Equity here is only the four figures
        somebody typed in — capital, revenue, expense, dividend. Nothing
        posts a trading result to it, so accumulated profit has no home and
        the difference lands in `imbalance` for the template to show. The
        honest number is the one worth rendering; a plug that forced the
        two sides to agree would hide exactly the thing worth seeing.
        """
        zero = Decimal("0.00")

        try:
            cash = get_total_base_currency_balance(book.pk)
        except ValidationError:
            # A currency with no exchange rate — report the cash we can
            # convert rather than 500-ing the whole page.
            cash = zero

        cari = CariAccount.objects.filter(book=book).aggregate(
            receivable=Sum("cached_balance", filter=Q(cached_balance__gt=0)),
            payable=Sum("cached_balance", filter=Q(cached_balance__lt=0)),
        )
        receivable = cari["receivable"] or zero
        payable = abs(cari["payable"] or zero)

        fixed = _sum_in_base(AssetFixedAsset, book, "value")
        capital = _sum_in_base(EquityCapital, book, "amount")
        revenue = _sum_in_base(EquityRevenue, book, "amount")
        expense = _sum_in_base(EquityExpense, book, "amount")
        dividend = _sum_in_base(EquityDivident, book, "amount")

        assets = cash + receivable + fixed
        equity = capital + revenue - expense - dividend
        liabilities = payable

        return {
            "eq_cash": cash,
            "eq_receivable": receivable,
            "eq_fixed": fixed,
            "eq_assets": assets,
            "eq_payable": payable,
            "eq_liabilities": liabilities,
            "eq_capital": capital,
            "eq_revenue": revenue,
            "eq_expense": expense,
            "eq_dividend": dividend,
            "eq_equity": equity,
            "eq_right_side": liabilities + equity,
            "eq_imbalance": assets - (liabilities + equity),
            "eq_balanced": abs(assets - (liabilities + equity)) < Decimal("0.01"),
        }

    def get_object(self):
        # Get the primary key from the URL
        pk = self.kwargs.get("pk")
        # Retrieve the Book object

        return get_object_or_404(Book, pk=pk)

    # def get_exchange_rate(self, from_currency, to_currency):
    #     ticker = f"{from_currency}{to_currency}=X"
    #     data = yf.Ticker(ticker)
    #     exchange_rate = data.history(period="1d")["Close"][0]
    #     return Decimal(exchange_rate)

    # def get_monthly_revenue_in_usd(self, start_date, end_date):
    #     book = self.get_object()
    #     revenues = EquityRevenue.objects.filter(
    #         book=book, date__gte=start_date, date__lt=end_date
    #     )
    #     total_revenue_usd = 0
    #     for revenue in revenues:
    #         if revenue.currency.code == "USD":
    #             amount_in_usd = revenue.amount
    #         else:
    #             exchange_rate = self.get_exchange_rate(revenue.currency.code, "USD")
    #             amount_in_usd = revenue.amount * exchange_rate
    #         total_revenue_usd += amount_in_usd
    #     return round(total_revenue_usd, 2)

    # def get_revenue_for_previous_months(self):
    #     now = timezone.now()
    #     first_day_of_current_month = datetime(now.year, now.month, 1)
    #     first_day_of_last_month = first_day_of_current_month - timedelta(days=1)
    #     first_day_of_last_month = datetime(
    #         first_day_of_last_month.year, first_day_of_last_month.month, 1
    #     )
    #     first_day_of_two_months_ago = first_day_of_last_month - timedelta(days=1)
    #     first_day_of_two_months_ago = datetime(
    #         first_day_of_two_months_ago.year, first_day_of_two_months_ago.month, 1
    #     )

    #     revenue_last_month = self.get_monthly_revenue_in_usd(
    #         first_day_of_last_month, first_day_of_current_month
    #     )
    #     revenue_two_months_ago = self.get_monthly_revenue_in_usd(
    #         first_day_of_two_months_ago, first_day_of_last_month
    #     )

    #     return revenue_two_months_ago, revenue_last_month

    # def calculate_growth_rate(self):
    #     revenue_two_months_ago, revenue_last_month = (
    #         self.get_revenue_for_previous_months()
    #     )
    #     if revenue_last_month == 0:
    #         return 0  # Avoid division by zero
    #     growth_rate = (
    #         (revenue_last_month - revenue_two_months_ago) / revenue_last_month
    #     ) * 100
    #     return round(growth_rate, 2)

    # def get_monthly_expenses_in_usd(self):
    #     book = self.get_object()
    #     # Get the first day of the current month
    #     now = timezone.now()
    #     first_day_of_month = datetime(now.year, now.month, 1)

    #     # Fetch all expenses from the beginning of the month until now
    #     expenses = EquityExpense.objects.filter(book=book, date__gte=first_day_of_month)

    #     total_expense_usd = 0
    #     for expense in expenses:
    #         if expense.currency.code == "USD":
    #             amount_in_usd = expense.amount
    #         else:
    #             exchange_rate = self.get_exchange_rate(expense.currency.code, "USD")
    #             amount_in_usd = expense.amount * exchange_rate
    #         total_expense_usd += amount_in_usd

    #     return round(total_expense_usd, 2)

    # def get_context_data(self, **kwargs):
    #     start_time = time.time()
    #     context = super().get_context_data(**kwargs)
    #     book = self.get_object()
    #     # ----------------------------
    #     # Below is for the total balance in cash accounts
    #     balance_usd = Decimal(
    #         CashAccount.objects.filter(book=book, currency=1).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     balance_eur = Decimal(
    #         CashAccount.objects.filter(book=book, currency=2).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     balance_try = Decimal(
    #         CashAccount.objects.filter(book=book, currency=3).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     eur_to_usd = self.get_exchange_rate("EUR", "USD")
    #     try_to_usd = self.get_exchange_rate("TRY", "USD")

    #     balance_eur_in_usd = Decimal(balance_eur) * Decimal(eur_to_usd)
    #     balance_try_in_usd = Decimal(balance_try) * Decimal(try_to_usd)

    #     balance = (
    #         Decimal(balance_usd)
    #         + Decimal(balance_eur_in_usd)
    #         + Decimal(balance_try_in_usd)
    #     )
    #     balance = round(balance, 2)

    #     context["balance"] = balance

    #     print(
    #         f"this is how long the balance equation takes: {(time.time() - start_time)}"
    #     )

    #     # ----------------------------
    #     now = timezone.now()
    #     first_day_of_month = datetime(now.year, now.month, 1)
    #     day_of_today = datetime(now.year, now.month, now.day)
    #     context["revenue"] = self.get_monthly_revenue_in_usd(
    #         first_day_of_month, day_of_today
    #     )
    #     context["expense"] = self.get_monthly_expenses_in_usd()
    #     context["burn"] = context["revenue"] - context["expense"]
    #     # Below is number of months you can survive, rounds it down to 2 decimals
    #     avg_burn = -1000
    #     context["runway"] = round((context["balance"] / abs(avg_burn)), 1)
    #     context["growth_rate"] = self.calculate_growth_rate()
    #     context["default_alive"] = ""
    #     book = self.get_object()
    #     stakeholders = StakeholderBook.objects.filter(book_id=book.pk)
    #     context["Stakeholders"] = stakeholders
    #     print(f"this is how long the execution takes: {(time.time() - start_time)}")
    #     return context


@method_decorator(login_required, name="dispatch")
class AddStakeholderBook(generic.edit.CreateView):
    model = StakeholderBook
    form_class = StakeholderBookForm
    template_name = "accounting/add_stakeholderbook.html"

    # below preselected the book field of the capital model
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {"book": book}

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )


# ------------------------------------------------------------------------------------------------
# equity functions:
@transaction.atomic
def handle_equity_transaction(
    book, amount, currency, equity_instance, equity_pk, cash_account
):
    import time

    # 1 Add Transaction
    # 2 Adjust Asset Cash
    # 3 adjust cashaccount balance
    start_time = time.time()
    is_amount_positive = True
    # 1
    cash_account = CashAccount.objects.get(pk=cash_account.pk)
    if isinstance(equity_instance, (EquityCapital, EquityRevenue)):
        cash_account.balance += amount
        is_amount_positive = True
    elif isinstance(equity_instance, (EquityExpense, EquityDivident)):
        cash_account.balance -= amount
        is_amount_positive = False
    else:
        raise ValidationError({"cash_account": "cash_account balance failed to update"})
    cash_account.save(update_fields=["balance"])

    print("the time it took:", "--- %s seconds ---" % (time.time() - start_time))

    # # 2
    # asset_cash, created = AssetCash.objects.get_or_create(book=book, currency=currency)
    # if created:
    #     asset_cash.balance = 0
    # asset_cash.balance += amount
    # asset_cash.save(update_fields=["balance"])

    # 3
    content_type = ContentType.objects.get_for_model(equity_instance)
    cash_transaction_entry = CashTransactionEntry.objects.create(
        book=book,
        content_type=content_type,
        content_pk=equity_pk,
        amount=amount,
        is_amount_positive=is_amount_positive,
        currency=currency,
        cash_account=cash_account,
    )
    print("the time2 it took:", "--- %s seconds ---" % (time.time() - start_time))
    print("all done")
    return True


def handle_expense_on_account(book, expense, member=None):
    """Post the credit for an expense somebody else settled.

    The cash path (handle_equity_transaction) credits a cash account and
    writes a CashTransactionEntry. There is nothing to credit here: the
    money left somebody's own pocket, not the book's. What the book gained
    is a debt to them, so the credit goes to their current account and the
    cash ledger is left alone — which is the whole point, since a cash
    entry would report money leaving an account it never sat in.

    Typed `adjustment` rather than `collection`, deliberately. A collection
    means money came in, and signals_accounts mirrors one into a Payment
    row that then shows in the tahsilat list; nothing was collected here,
    so nothing should appear there. `adjustment` is mirrored to no Payment
    at all.

    The movement points back at the expense through the generic source FK,
    so the two halves are one document rather than two rows that happen to
    agree — and so CariMovement.entered_rate can ask the expense what rate
    it was recorded at, via EquityExpense.ledger_exchange_rate.
    """
    return CariMovement.objects.create(
        cari=expense.paid_by_cari,
        book=book,
        date=expense.date,
        # Negative: the book owes them. Same sign convention the cari
        # detail page reads, where a negative balance is a payable.
        amount=-abs(expense.amount),
        currency=expense.currency,
        movement_type="adjustment",
        source_type=ContentType.objects.get_for_model(EquityExpense),
        source_id=expense.pk,
        description=(
            expense.description
            or (expense.category.name if expense.category else "")
            or "Expense paid on the book's behalf"
        )[:300],
        created_by=member,
    )


def post_expense(book, expense, member=None):
    """Apply an expense's effect on the ledger, whichever funded it.

    One definition, so creating and editing cannot drift: an edit unposts
    and re-posts through this same pair rather than working out the
    difference between two states. Reversing and re-applying is more work
    for the database and far less work to be sure of — a diff has to be
    right about every field that moved, while this only has to be right
    about one entry at a time.
    """
    if expense.cash_account_id:
        return handle_equity_transaction(
            book, expense.amount, expense.currency,
            expense, expense.pk, expense.cash_account,
        )
    return handle_expense_on_account(book, expense, member)


def unpost_expense(expense):
    """Undo what post_expense did, reading the funding off the row given.

    Call it with the expense AS STORED, not as edited: it is the old cash
    account that has to be given the money back, and the old movement that
    has to go.
    """
    content_type = ContentType.objects.get_for_model(EquityExpense)
    if expense.cash_account_id:
        # F() rather than read-modify-write: two people editing two
        # expenses out of one account must not overwrite each other's
        # balance. Giving money back cannot go negative, so nothing here
        # needs the validation CashAccount.save() would run.
        CashAccount.objects.filter(pk=expense.cash_account_id).update(
            balance=F("balance") + expense.amount
        )
        CashTransactionEntry.objects.filter(
            content_type=content_type, content_pk=expense.pk
        ).delete()
    else:
        # post_delete recomputes the account's balance — see
        # signals_accounts.recompute_after_delete.
        CariMovement.objects.filter(
            source_type=content_type, source_id=expense.pk
        ).delete()


# -------


@method_decorator(login_required, name="dispatch")
class AddEquityCapital(generic.edit.CreateView):
    model = EquityCapital
    form_class = EquityCapitalForm
    template_name = "accounting/add_equity_capital.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = Book.objects.filter(pk=self.kwargs.get("pk")).first()
        context["base_currency"] = fx_context_json(book)
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ["accounting/partials/capital_form.html"]
        return [self.template_name]

    # # This sends to the form data the book we are in. We need this so we can show the cash accounts only associated with this book.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below pre-selects the book field of the capital model in the form
    # below is available in CreateView and UpdateViews
    # Usage: It returns a dictionary where the keys are the form field names and the values are the initial data for those fields.
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        return {
            "book": book,
        }

    # revert back all db changes if any errors while in form_valid
    @transaction.atomic
    def form_valid(self, form):

        # get the book pk from the url:
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)

        # get the capital amount from form post data
        amount = form.cleaned_data.get("amount")
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)

        # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency

        # The contributor must be a stakeholder of this book, but the
        # contribution does not move their holding: shares are issued as
        # ShareIssuance rows on the book's shares page, and a bare += here
        # would be wiped by the next recompute anyway.
        member = form.cleaned_data["member"]
        if not StakeholderBook.objects.filter(member=member, book=book).exists():
            form.add_error("member", "Couldn't fetch the member properly")
            return self.form_invalid(form)

        # get the new created object (EquityCapital)
        # form.save(commit=False) creates a model instance before saving it to the database
        self.object = form.save(commit=False)
        self.object.currency = currency
        # now save to the database
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Capital added successfully!',
                'redirect_url': self.get_success_url()
            })

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            }, status=400)
            
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddEquityRevenue(generic.edit.CreateView):
    model = EquityRevenue
    form_class = EquityRevenueForm
    template_name = "accounting/add_equity_revenue.html"

    def get_template_names(self):
        if self.request.headers.get('HX-Request') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ["accounting/partials/revenue_form.html"]
        return [self.template_name]

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {
            "book": book,
        }

    # revert back all db changes if any errors while in form_valid
    @transaction.atomic
    def form_valid(self, form):

        # get the book pk from the url:
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # revenue amount
        amount = form.cleaned_data.get("amount")

        # Get the selected cash account from the form
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)
        # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency
        self.object = form.save(commit=False)
        self.object.currency = currency
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Revenue added successfully!',
                'redirect_url': self.get_success_url()
            })

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            }, status=400)

        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


class EquityExpensePage:
    """The shared half of the two expense pages.

    Recording an expense and correcting one are the same form over the same
    row, so they are the same page — reached at different URLs and landing
    on the entry either way. Only what happens on save differs, which is
    all the two subclasses below hold.
    """

    model = EquityExpense
    form_class = EquityExpenseForm
    template_name = "accounting/add_equity_expense.html"

    def get_book(self):
        return Book.objects.get(pk=self.kwargs.get("pk"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = Book.objects.filter(pk=self.kwargs.get("pk")).first()
        context["base_currency"] = fx_context_json(book)
        context["book"] = book
        context["date_value"] = self._date_value(context.get("form"))
        # Whether the currency is already decided — see the JS that reads
        # it. An expense being edited HAS a currency, chosen deliberately,
        # and the account it was funded through must not be allowed to
        # propose over the top of it.
        context["currency_is_settled"] = self._currency_is_settled(
            context.get("form")
        )
        # The full page renders its own controls rather than {{ form.as_p }},
        # so it needs the options as data. The form's querysets stay the
        # authority on what is ACCEPTED — these only decide what is offered,
        # and both are scoped to the same book.
        form = context.get("form")
        if form is not None:
            context["cash_accounts"] = form.fields["cash_account"].queryset
            context["cari_options"] = [
                {
                    "id": c.pk,
                    "code": c.code,
                    "name": c.name,
                    "type": c.get_type_display(),
                    "currency_id": c.default_currency_id,
                    "currency_code": c.default_currency.code,
                }
                for c in form.fields["paid_by_cari"].queryset
            ]
            context["categories"] = form.fields["category"].queryset
            context["currencies"] = CurrencyCategory.objects.all().order_by("code")
        # What the entry actually did, read back off the ledger rather than
        # recomputed from the form — the point of landing here is to see
        # that both halves of it exist.
        context["ledger_movement"] = self.ledger_movement()
        return context

    def _date_value(self, form):
        """What the date input shows — always ISO, whatever the locale.

        The raw POST first, so a rejected submit keeps what was typed; then
        the stored date, which is the whole reason an edit does not open on
        today; then today, for a new one.

        Never form.date.value: on an edit that hands back a date object,
        which the template renders through the active locale as
        "26 Ağustos 2026" — and <input type="date"> silently drops anything
        that is not ISO, so the field would come up empty and the edit would
        look like it had lost the date.
        """
        posted = form.data.get("date") if form is not None else None
        if posted:
            return posted
        stored = getattr(self.object, "date", None) if self.object else None
        if stored:
            return stored.isoformat()
        return timezone.localdate().isoformat()

    def _currency_is_settled(self, form) -> bool:
        """True when the currency must be left exactly as it is.

        The page proposes the funding account's currency as you pick one,
        which is right while an expense is being written and wrong the
        moment one already exists: expense 54 is 939.70 TRY settled through
        a dollar account, and proposing over it turned it back into dollars
        on open. A stored currency is an answer already given.
        """
        if self.object is not None and self.object.pk:
            return True
        return bool(form is not None and form.data.get("currency"))

    def ledger_movement(self):
        """The cari movement this expense posted, if it posted one."""
        expense = getattr(self, "object", None)
        if expense is None or not expense.pk or not expense.paid_by_cari_id:
            return None
        return (
            CariMovement.objects
            .filter(
                source_type=ContentType.objects.get_for_model(EquityExpense),
                source_id=expense.pk,
            )
            .select_related("currency", "cari")
            .first()
        )

    def get_template_names(self):
        if self.request.headers.get('HX-Request') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ["accounting/partials/expense_form.html"]
        return [self.template_name]

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["book"] = self.get_book()
        return kwargs

    def _recorded_message(self) -> str:
        """What just happened, in the terms the entry was made in."""
        expense = self.object
        amount = f"{expense.amount} {expense.currency.code}"
        if expense.paid_by_cari_id:
            return _g("%(amount)s expense recorded — %(account)s is owed it.") % {
                "amount": amount, "account": expense.paid_by_cari.name,
            }
        return _g("%(amount)s expense recorded, paid from %(account)s.") % {
            "amount": amount, "account": expense.cash_account.name,
        }

    def get_success_url(self) -> str:
        """The expense's own page.

        Not the book, which reports a position that one expense moves by an
        amount too small to see, and not the list, which says an entry
        exists without showing what it did. Its own page shows the figures
        back, the ledger row it posted and the account that carries it —
        and is where a correction is made, so the answer to "is that
        right?" and the way to fix it are the same screen.
        """
        return reverse(
            "accounting:edit_equity_expense",
            kwargs={"pk": self.kwargs.get("pk"), "expense_pk": self.object.pk},
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            }, status=400)

        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)

    def _respond(self, form):
        messages.success(self.request, self._recorded_message())
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': self._recorded_message(),
                'redirect_url': self.get_success_url()
            })
        return HttpResponseRedirect(self.get_success_url())


@method_decorator(login_required, name="dispatch")
class AddEquityExpense(EquityExpensePage, generic.edit.CreateView):

    # below pre-selecting the book field in the form according to the pk in the url
    # get initial is a function that is applicable to update and create views like these forms.
    def get_initial(self):
        # Set the initial value of the book field to the book in the URL
        return {"book": self.get_book()}

    @transaction.atomic
    def form_valid(self, form):
        book = self.get_book()
        # Exactly one funding source is set — the form's clean() and the
        # model's check constraint both say so, so post_expense is choosing
        # between two funded expenses, never checking for an unfunded one.
        self.object = form.save(commit=False)
        self.object.currency = form.cleaned_data.get("currency")
        self.object.save()
        try:
            post_expense(book, self.object,
                         getattr(self.request.user, "member", None))
        except ValidationError as exc:
            # The one that reaches here is CashAccount's "balance cannot be
            # less than zero" — a real answer, and better shown on the form
            # than as a 500.
            form.add_error("cash_account", _g("That account does not hold enough: %s") % exc.messages[0])
            return self.form_invalid(form)
        return self._respond(form)


@method_decorator(login_required, name="dispatch")
class DeleteEquityExpense(View):
    """Remove an expense that should never have been one.

    Not every wrong entry is a wrong figure. An expense recorded for
    something that turns out not to be the book's expense at all — a tax
    paid on another account's behalf, say — cannot be edited into what it
    should have been, because what it should have been is a different kind
    of record. It has to go, and then the right one is made.

    POST only: a link that a crawler or a prefetch can follow must not be
    able to unwind a ledger entry.
    """

    def post(self, request, pk, expense_pk):
        expense = get_object_or_404(EquityExpense, pk=expense_pk, book_id=pk)
        note = _g("%(amount)s expense deleted.") % {
            "amount": f"{expense.amount} {expense.currency.code}",
        }
        with transaction.atomic():
            # Give the cash back or drop the debt first — deleting the row
            # on its own would leave whichever it posted standing, with
            # nothing left to explain it.
            unpost_expense(expense)
            expense.delete()
        messages.success(request, note)
        return HttpResponseRedirect(
            reverse("accounting:equity_expense_list", kwargs={"pk": pk})
        )


@method_decorator(login_required, name="dispatch")
class EditEquityExpense(EquityExpensePage, generic.edit.UpdateView):
    """Correct an expense, including what funded it.

    The edit is a reversal and a fresh posting, not an adjustment of the
    rows already there. Money may have moved between two cash accounts, or
    stopped being cash at all and become a debt to somebody — there is no
    single row to amend in that case, and working out which of the four
    transitions this is would be four chances to be wrong. Unposting the
    stored row and posting the edited one is right for all of them.
    """

    pk_url_kwarg = "expense_pk"

    def get_queryset(self):
        # Scoped to the book in the URL: an expense reached through the
        # wrong book's URL is a 404, not somebody else's row to edit.
        return EquityExpense.objects.filter(book_id=self.kwargs.get("pk"))

    @transaction.atomic
    def form_valid(self, form):
        book = self.get_book()
        # The row AS STORED — it is the old cash account that gets the
        # money back and the old movement that goes. form.save(commit=False)
        # mutates self.object in place, so this has to be read first, and
        # from the database rather than from the instance being edited.
        stored = EquityExpense.objects.get(pk=self.object.pk)
        unpost_expense(stored)

        self.object = form.save(commit=False)
        self.object.currency = form.cleaned_data.get("currency")
        self.object.save()
        try:
            post_expense(book, self.object,
                         getattr(self.request.user, "member", None))
        except ValidationError as exc:
            form.add_error("cash_account", _g("That account does not hold enough: %s") % exc.messages[0])
            return self.form_invalid(form)
        return self._respond(form)
@method_decorator(login_required, name="dispatch")
class AddEquityDivident(generic.edit.CreateView):
    model = EquityDivident
    form_class = EquityDividentForm
    template_name = "accounting/add_equity_divident.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = Book.objects.filter(pk=self.kwargs.get("pk")).first()
        context["base_currency"] = fx_context_json(book)
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ["accounting/partials/dividend_form.html"]
        return [self.template_name]

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)

        # divident amount given to stakeholder
        amount = form.cleaned_data.get("amount")
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)
            # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency
        self.object = form.save(commit=False)
        self.object.currency = currency
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Dividend paid successfully!',
                'redirect_url': self.get_success_url()
            })

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            }, status=400)

        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddFixedAsset(generic.edit.CreateView):
    model = AssetFixedAsset
    form_class = AssetFixedAssetForm
    template_name = "accounting/add_fixed_asset.html"

    def get_initial(self):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        return {"book": book, "currency": 1}

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )


@method_decorator(login_required, name="dispatch")
class EditFixedAsset(generic.edit.UpdateView):
    model = AssetFixedAsset
    form_class = AssetFixedAssetForm
    template_name = "accounting/add_fixed_asset.html"
    pk_url_kwarg = "asset_pk"

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )


# do not remember what this did
@method_decorator(login_required, name="dispatch")
class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)


@method_decorator(login_required, name="dispatch")
class SalesView(generic.TemplateView):
    template_name = "accounting/sales_report.html"


@method_decorator(login_required, name="dispatch")
class EquityExpenseList(generic.ListView):
    model = EquityExpense
    template_name = "accounting/equity_expense_list.html"

    def get_queryset(self):
        # Scoped to the book in the URL — the page is reached from that
        # book's detail view, so showing every book's expenses would be
        # wrong on a multi-book install (and leak between them).
        book_pk = self.kwargs.get("pk")
        return (
            EquityExpense.objects.filter(book=book_pk)
            .select_related("category", "cash_account", "paid_by_cari", "currency")
            .order_by("-date", "-pk")
        )


# The relations cash_entry_heading reads. Followed up front, because
# reaching them one row at a time is how a 50-row page turns into 100
# extra queries.
DESCRIPTION_RELATIONS = ("cari", "member", "supplier", "category")


def _source_queryset(model):
    """A queryset for a cash entry's source, with description FKs followed."""
    names = {field.name for field in model._meta.fields if field.is_relation}
    related = [name for name in DESCRIPTION_RELATIONS if name in names]
    if "member" in related:
        # Member.__str__ reads the user's name, which is another hop.
        related.append("member__user")
    queryset = model._default_manager.all()
    return queryset.select_related(*related) if related else queryset


def fx_context_json(book):
    """The book's base currency as JSON, for the forms' rate converter.

    A dict would render as Python's repr in a template — single quotes, not
    JSON — so it is serialised here rather than in the template.
    """
    if book is None:
        return "null"
    base = book.effective_base_currency
    return json.dumps({"id": base.pk, "code": base.code, "symbol": base.symbol})


def running_cash_balances(book_pk):
    """{entry pk: (account balance, book total)} across a book's whole ledger.

    Worked out from the rows every time they are shown, rather than stamped
    onto each row when it is written. A stored running total is only correct
    until something upstream of it changes, and things upstream do change:
    backdating a payment moves it into the middle of the sequence, editing an
    amount alters every total after it, cancelling removes a row entirely.
    Each of those left the stored figures describing a past that no longer
    happened, and needed a repair command run afterwards to become true again.
    Derived figures cannot go stale.

    Both columns come from one query, as window functions over the book:
    the account balance partitioned by cash account, the book total across
    all of them.

    The window has to see the whole book, so this cannot be folded into the
    page's own queryset — a WHERE runs before the window, and filtering to
    one cash account first would total only that account's rows and call the
    result the book's. Hence a separate pass keyed by primary key.
    """
    signed_amount = Case(
        When(is_amount_positive=True, then=Coalesce(F("amount"), Value(0))),
        default=-Coalesce(F("amount"), Value(0)),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    signed_base = Case(
        When(
            is_amount_positive=True,
            then=Coalesce(F("amount_in_base_currency"), Value(0)),
        ),
        default=-Coalesce(F("amount_in_base_currency"), Value(0)),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    # The order the money moved in, and the order the page shows: the date
    # first, then when it was recorded, then the id so equal timestamps still
    # have exactly one answer.
    sequence = [F("date").asc(), F("created_at").asc(), F("pk").asc()]

    rows = (
        CashTransactionEntry.objects.filter(book=book_pk)
        .annotate(
            account_running=Window(
                Sum(signed_amount),
                partition_by=[F("cash_account_id")],
                order_by=sequence,
            ),
            book_running=Window(Sum(signed_base), order_by=sequence),
        )
        .values_list("pk", "account_running", "book_running")
    )
    return {pk: (account, book) for pk, account, book in rows}


def cash_entry_heading(obj):
    """The line that identifies a cash row, above whatever was typed on it.

    What identifies a row depends on what moved the money: a collection or
    payment is identified by the account it was with, a capital deposit or
    dividend by the member, an expense by its category. All three answer
    "what is this", where the description answers "which one".

    Kept apart from the description rather than used as a fallback for it.
    They are not alternatives, and folding them into one field meant
    whichever was checked first hid the other — which is how a payment that
    had been given a description stopped naming its account.
    """
    if obj is None:
        return ""
    for field in ("cari", "member", "supplier", "category"):
        related = getattr(obj, field, None)
        if related is not None:
            return str(related)
    return ""


def describe_cash_entry_source(obj, accounts=None):
    """The line of text that says what a cash entry was for.

    Whatever was typed when the row was entered. A source with no such
    field — a currency exchange has none — is described from what it is
    instead, because a blank column teaches the reader nothing. Who it was
    or what it was is cash_entry_heading's job, shown alongside this.

    `accounts` is a {pk: CashAccount} map for the book, so describing an
    exchange costs no extra queries; the view already loads it for the
    filter.
    """
    if obj is None:
        # The source row was deleted out from under the entry.
        return ""

    for field in ("description", "note"):
        text = (getattr(obj, field, "") or "").strip()
        if text:
            return text

    # An exchange or transfer: name the two sides.
    from_id = getattr(obj, "from_cash_account_id", None)
    if from_id is not None and accounts:
        source = accounts.get(from_id)
        target = accounts.get(getattr(obj, "to_cash_account_id", None))
        if source and target:
            # InTransfer moves one amount; CurrencyExchange has two.
            out = getattr(obj, "from_amount", None) or getattr(obj, "amount", None)
            into = getattr(obj, "to_amount", None) or out
            left = f"{source.currency.symbol}{out:,.2f}"
            right = f"{target.currency.symbol}{into:,.2f}"
            if source.currency_id == target.currency_id:
                # Same currency both sides, so the symbols cannot say which
                # account is which. Name them. Across currencies the symbols
                # already do, and the names would only repeat themselves.
                left += f" {source.name}"
                right += f" {target.name}"
            return f"{left} → {right}"

    return ""


@method_decorator(login_required, name="dispatch")
class CashTransactionEntryList(generic.ListView):
    model = CashTransactionEntry
    template_name = "accounting/cash_transaction_entry_list.html"

    paginate_by = 50

    def get_selected_account(self, accounts):
        """The cash account being filtered to, or None for all of them."""
        raw = self.request.GET.get("account") or ""
        if raw.isdigit():
            return accounts.get(int(raw))
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = Book.objects.get(pk=self.kwargs.get("pk"))
        context["base_currency"] = book.effective_base_currency
        context["base_currency_symbol"] = str(book.effective_base_currency.symbol)
        context["book"] = book

        accounts = {
            a.pk: a
            for a in CashAccount.objects.filter(book=book).select_related("currency")
        }
        # One query for every tab's count, rather than one per tab.
        counts = dict(
            CashTransactionEntry.objects.filter(book=book)
            .values_list("cash_account")
            .annotate(n=Count("pk"))
        )
        context["cash_accounts"] = [
            {"account": a, "count": counts.get(a.pk, 0)}
            for a in sorted(accounts.values(), key=lambda a: (a.name, a.currency.code))
        ]
        context["total_count"] = sum(counts.values())
        context["selected_account"] = self.get_selected_account(accounts)

        # entry.content is a GenericForeignKey, so reading it in the template
        # loop would cost a query per row. Group the page's rows by content
        # type and fetch each source table once instead.
        entries = list(context["object_list"])
        by_type = {}
        for entry in entries:
            by_type.setdefault(entry.content_type_id, set()).add(entry.content_pk)

        sources = {}
        for content_type in ContentType.objects.filter(pk__in=by_type):
            model = content_type.model_class()
            if model is None:
                continue  # a model that no longer exists in the codebase
            sources[content_type.pk] = (
                _source_queryset(model).in_bulk(by_type[content_type.pk])
            )

        balances = running_cash_balances(book.pk)
        for entry in entries:
            source = sources.get(entry.content_type_id, {}).get(entry.content_pk)
            entry.source_heading = cash_entry_heading(source)
            entry.source_description = describe_cash_entry_source(source, accounts)
            entry.account_running, entry.book_running = balances.get(
                entry.pk, (None, None)
            )
        context["object_list"] = entries
        return context

    def get_template_names(self):
        # An htmx request is a filter or page click from a page already on
        # screen, so it gets only the part that changes. Same context, same
        # markup — the full page renders that partial through an include.
        if self.request.headers.get("HX-Request"):
            return ["accounting/partials/cash_transaction_results.html"]
        return [self.template_name]

    def get_queryset(self):
        # Ordered here rather than by piping the page through
        # |dictsortreversed in the template: that sorted only the rows the
        # paginator had already chosen, so "newest first" was true within a
        # page and false across the list. select_related keeps the row loop
        # off a query per cash account, currency and content type.
        #
        # By `date` — when the money moved — not `created_at`, which is when
        # someone typed it in. Backdating an entry used to file it under the
        # day it was entered. created_at still breaks ties, so several rows
        # sharing a date keep the order they were recorded in.
        book_pk = self.kwargs.get("pk")
        queryset = (
            CashTransactionEntry.objects
            .filter(book=book_pk)
            .select_related("cash_account", "currency", "content_type")
            .order_by("-date", "-created_at", "-pk")
        )
        # ?account=<pk> narrows to one cash account. Filtered on the id
        # straight from the query string rather than resolving the account
        # first: an id from another book simply matches nothing, which is
        # the right answer for a hand-edited URL.
        account = self.request.GET.get("account") or ""
        if account.isdigit():
            queryset = queryset.filter(cash_account_id=int(account))
        return queryset


# @method_decorator(login_required, name='dispatch')
# class InvoiceCreateView(generic.CreateView):
#     model = Invoice
#     form_class = InvoiceForm
#     template_name = 'accounting/create_invoice.html'
#     success_url = reverse_lazy('operating:index')

#     def get_context_data(self, **kwargs):
#         # Add the invoice form and formset for items
#         context = super().get_context_data(**kwargs)
#         InvoiceItemFormSet = modelformset_factory(InvoiceItem, form=InvoiceItemForm, extra=1)
#         context['item_formset'] = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
#         return context

#     def form_valid(self,form):
#         invoice = form.save()
#         # Now that the invoice is saved, it has a primary key
#         # Get the formset for invoice items
#         item_formset = InvoiceItemFormSet(self.request.POST)
#         # products = self.request.POST.getlist('products')
#         if item_formset.is_valid():
#             total_amount = 0  # Initialize total_amount to 0
#             items_to_save = []  # Collect InvoiceItem instances to save later
#             # For each form in the formset, create an InvoiceItem entry
#             for item_form in item_formset:
#                 product = item_form.cleaned_data.get('product')
#                 quantity = item_form.cleaned_data.get('quantity')
#                 price = item_form.cleaned_data.get('price')
#                 if product and quantity is not None and price is not None:
#                     item = InvoiceItem(
#                         invoice=invoice,
#                         product=product,
#                         quantity=quantity,
#                         price=price
#                     )
#                     items_to_save.append(item)
#                     # Accumulate total amount
#                     total_amount += quantity * price


#             InvoiceItem.objects.bulk_create(items_to_save)
#             invoice.total_amount = total_amount
#             invoice.save()  # Save the updated invoice
#         return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class MakeInTransfer(View):
    """One page, two kinds of transfer.

    Cash mode moves money between the book's own cash accounts — the
    balances and the cash ledger both change. Account mode moves a
    balance between two current accounts (a virman): the debt is
    reassigned, no cash goes anywhere.

    They share a page because the operator's question is the same one
    ("move X from here to there") and splitting it into two menu entries
    only makes them hunt. They do NOT share a form: the fields, the
    validation and the rows written have nothing in common, so each mode
    binds its own form and the other renders unbound beside it.

    Was a CreateView. Two models with two forms is exactly what that
    class cannot express — get_form_class() has no access to the POST
    that decides which one applies.
    """

    template_name = "accounting/make_in_transfer.html"
    MODES = ("cash", "cari")

    def get_book(self):
        return get_object_or_404(Book, pk=self.kwargs.get("pk"))

    def _mode(self, source):
        mode = source.get("mode") or "cash"
        return mode if mode in self.MODES else "cash"

    def render_page(self, book, mode, cash_form=None, cari_form=None):
        return render(self.request, self.template_name, {
            "book": book,
            "mode": mode,
            "form": cash_form or InTransferForm(book=book, initial={"book": book}),
            "cari_form": cari_form or CariTransferForm(book=book, initial={"book": book}),
            "cash_accounts": CashAccount.objects.filter(book=book).order_by("name"),
            # A cari's cached balance is a BASE-currency figure while the
            # transfer is typed in whichever currency is picked, so the
            # page needs to know which currency that is to convert.
            #
            # Deliberately settings.BASE_CURRENCY_CODE and NOT the book's
            # own base: CariMovement.save() and CariAccount's balances
            # convert against the former, so taking the latter here would
            # let the page label and convert against one currency while the
            # ledger used another — invisible today, since every book is
            # USD, and silently wrong the day one is not.
            "base_currency": CurrencyCategory.objects.filter(
                code=getattr(settings, "BASE_CURRENCY_CODE", "USD")
            ).first(),
        })

    def get(self, request, pk):
        book = self.get_book()
        return self.render_page(book, self._mode(request.GET))

    def post(self, request, pk):
        book = self.get_book()
        mode = self._mode(request.POST)
        if mode == "cari":
            return self.post_cari(request, book)
        return self.post_cash(request, book)

    # -- cash → cash ------------------------------------------------------
    @transaction.atomic
    def post_cash(self, request, book):
        form = InTransferForm(request.POST, book=book)
        if not form.is_valid():
            return self.render_page(book, "cash", cash_form=form)

        amount = form.cleaned_data["amount"]
        from_cash_account = form.cleaned_data["from_cash_account"]
        to_cash_account = form.cleaned_data["to_cash_account"]
        if not from_cash_account or not to_cash_account:
            form.add_error(None, "Please select valid cash accounts for the transfer.")
            return self.render_page(book, "cash", cash_form=form)

        from_cash_account.balance -= amount
        from_cash_account.save(update_fields=["balance"])

        to_cash_account.balance += amount
        to_cash_account.save(update_fields=["balance"])

        obj = form.save(commit=False)
        obj.currency = from_cash_account.currency
        obj = form.save()

        content_type = ContentType.objects.get_for_model(obj)

        CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=obj.pk,
            amount=amount,
            is_amount_positive=False,
            currency=from_cash_account.currency,
            cash_account=from_cash_account,
        )

        CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=obj.pk,
            amount=amount,
            is_amount_positive=True,
            currency=to_cash_account.currency,
            cash_account=to_cash_account,
        )

        messages.success(request, _g("Moved %(amount)s from %(src)s to %(dst)s.") % {
            "amount": f"{from_cash_account.currency.symbol}{amount}",
            "src": from_cash_account.name,
            "dst": to_cash_account.name,
        })
        return redirect(self.success_url(book, "cash"))

    # -- cari → cari ------------------------------------------------------
    @transaction.atomic
    def post_cari(self, request, book):
        form = CariTransferForm(request.POST, book=book)
        if not form.is_valid():
            return self.render_page(book, "cari", cari_form=form)

        transfer = form.save(commit=False)
        transfer.book = book
        transfer.created_by = getattr(request.user, "member", None)
        try:
            transfer.save()
        except ValidationError as exc:
            # The model's own clean() guards the same rules the form does,
            # so this is the belt to the form's braces rather than a path
            # the UI can normally reach.
            form.add_error(None, exc.messages)
            return self.render_page(book, "cari", cari_form=form)
        transfer.post(user=request.user)

        messages.success(request, _g("Moved %(amount)s from %(src)s to %(dst)s.") % {
            "amount": f"{transfer.amount} {transfer.currency.code}",
            "src": transfer.from_cari.name,
            "dst": transfer.to_cari.name,
        })
        return redirect(self.success_url(book, "cari"))

    def success_url(self, book, mode):
        base = reverse("accounting:make_in_transfer", kwargs={"pk": book.pk})
        return f"{base}?mode={mode}"


@method_decorator(login_required, name="dispatch")
class MakeCurrencyExchange(generic.edit.FormView):
    form_class = CurrencyExchangeForm
    template_name = "accounting/make_currency_exchange.html"

    def get_context_data(self, **kwargs):
        # The page needs the book itself for the breadcrumb, and the cash
        # balances beside the form — picking which account to draw from is
        # guesswork without them.
        context = super().get_context_data(**kwargs)
        book = Book.objects.get(pk=self.kwargs.get("pk"))
        context["book"] = book
        context["cash_accounts"] = (
            CashAccount.objects.filter(book=book)
            .select_related("currency")
            .order_by("currency__code", "name")
        )
        return context

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:make_currency_exchange", kwargs={"pk": self.kwargs.get("pk")}
        )

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Process the form data
        from_amount = form.cleaned_data["from_amount"]
        to_amount = form.cleaned_data["to_amount"]

        from_cash_account = form.cleaned_data["from_cash_account"]
        from_cash_account.balance -= from_amount
        from_cash_account.save(update_fields=["balance"])

        to_cash_account = form.cleaned_data["to_cash_account"]
        to_cash_account.balance += to_amount
        to_cash_account.save(update_fields=["balance"])

        self.object = form.save()

        content_instance = self.object
        content_pk = self.object.pk
        content_type = ContentType.objects.get_for_model(content_instance)

        from_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=from_amount,
            is_amount_positive=False,
            currency=from_cash_account.currency,
            cash_account=from_cash_account,
        )

        to_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=to_amount,
            is_amount_positive=True,
            currency=to_cash_account.currency,
            cash_account=to_cash_account,
        )

        # Add your processing logic here
        return super().form_valid(form)


# below are added after august 4, 2025 and for the new cogs system

# accounting.py (or similar location)


class CreateAssetInventoryRawMaterialGood(generic.CreateView):
    model = AssetInventoryRawMaterial
    form_class = AssetInventoryRawMaterialGoodForm
    template_name = "accounting/create_asset_inventory_raw_material_good.html"
    success_url = reverse_lazy(
        "accounting:create_asset_inventory_raw_material_good", kwargs={"pk": "pk"}
    )

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book}

    # def get_success_url(self):
    #     return reverse_lazy(
    #         "accounting:create_asset_inventory_raw_material", kwargs={"pk": self.kwargs.get("pk")}
    #     )


# class RawGoodsReceipt(View):
#     template_name = "accounting/raw_goods_receipt.html"

#     def form_invalid(self, request, form, formset, error_message=None):
#         return render(
#             request,
#             self.template_name,
#             {
#                 "form": form,
#                 "formset": formset,
#                 "error_message": error_message
#                 or "There were errors in your submission.",
#             },
#         )

#     # *args is tuple
#     # **kwargs is dictionary
#     def get(self, request, *args, **kwargs):
#         # print("your user information is:", request.user.member)
#         book_pk = kwargs.get("pk")
#         book = Book.objects.get(pk=book_pk)
#         form = RawMaterialGoodsReceiptForm(book=book)
#         # formset = GoodsReceiptItemFormSet()
#         formset = RawGoodsReceiptItemFormSet(prefix="receiveditem_set")
#         return render(request, self.template_name, {"form": form, "formset": formset})

#     def post(self, request, *args, **kwargs):
#         # self is the instance of the view, handling the request.
#         # CBVs are just Python classes, and self lets you access all the class's methods and attributes (e.g., self.model, self.template_name, self.object etc).
#         # Without it, your method wouldn’t be able to store or reuse data across other methods of the same view.

#         # request is the HttpRequest object that contains metadata about the request, such as form data, user information, and more.
#         # for example, request.POST contains the data submitted in a POST request.
#         # request.FILES, request.user, request.method (Session data, cookies, headers, etc.)
#         # You literally can’t process form submissions without it.

#         book_pk = kwargs.get("pk")
#         book = Book.objects.get(pk=book_pk)
#         form = RawMaterialGoodsReceiptForm(request.POST, book=book)
#         formset = RawGoodsReceiptItemFormSet(request.POST, prefix="receiveditem_set")
#         if form.is_valid() and formset.is_valid():
#             try:
#                 with transaction.atomic():
#                     # tz the form and formset data
#                     # Save the raw goods receipt and items
#                     raw_goods_receipt = form.save(commit=False)
#                     raw_goods_receipt.book = book
#                     raw_goods_receipt.save()
#                     items = formset.save(commit=False)
#                     # asset_accounts_receivable = AssetAccountsReceivable(book=book,)
#                     for item in items:
#                         item.goods_receipt = raw_goods_receipt
#                         item.raw_material.unit_cost = item.unit_cost
#                         item.raw_material.save(update_fields=["unit_cost"])
#                         item.save()
#                     payment_status = form.cleaned_data.get("payment_status")
#                     receipt_total_cost = raw_goods_receipt.total_cost()
#                     if payment_status:
#                         # If the payment status is paid, update the cash account
#                         cash_account = form.cleaned_data.get("cash_account")
#                         # cash_account = CashAccount.objects.get(cash_account)
#                         new_cash_account_balance = (
#                             cash_account.balance - receipt_total_cost
#                         )
#                         cash_account.balance = new_cash_account_balance
#                         cash_account.save(update_fields=["balance"])
#                         CashTransactionEntry_object = (
#                             CashTransactionEntry.objects.create(
#                                 book=book,
#                                 value=receipt_total_cost,
#                                 is_amount_positive=False,
#                                 type="purchase",
#                                 account=cash_account,
#                                 account_balance=cash_account.balance,
#                             )
#                         )
#                         CashTransactionEntry_object.save()
#                     else:

#                         liability_accounts_payable = LiabilityAccountsPayable.objects.create(
#                             supplier=raw_goods_receipt.supplier,
#                             book=book,
#                             amount=receipt_total_cost,
#                             is_amount_positive=False,
#                             raw_goods_receipt=raw_goods_receipt,
#                             # invoice
#                             # currency=raw_goods_receipt.currency,
#                         )
#                         liability_accounts_payable.save()

#                     return render(
#                         request,
#                         self.template_name,
#                         {
#                             "form": form,
#                             "formset": formset,
#                             "message": "Receipt created successfully!",
#                         },
#                     )
#             except Exception as e:
#                 form.add_error(None, f"An unexpected error occurred: {e}")
#                 return self.form_invalid(
#                     request,
#                     form,
#                     formset,
#                     error_message="An unexpected error occurred while processing your request.",
#                 )

#         # If invalid, print errors for debugging
#         print("Form errors:", form.errors)
#         print("Formset errors:", formset.errors)
#         return self.form_invalid(request, form, formset)


# # api calls
# def asset_inventory_raw_material_lookup(request, pk):
#     book = get_object_or_404(Book, pk=pk)
#     if request.method == "GET":
#         query = request.GET.get("{{ form.prefix }}-raw_material_name", "")
#         if query:
#             # raw_materials = AssetInventoryRawMaterial.objects.filter(name__icontains=query)
#             matches = AssetInventoryRawMaterial.objects.filter(
#                 name__icontains=query, book=book
#             ).values_list("name", flat=True)[:5]
#         else:
#             matches = AssetInventoryRawMaterial.objects.none()
#         # data = [{"id": match.pk, "name": match.name} for match in matches]
#         return render(
#             request,
#             "partials/material_suggestions.html",
#             {"materials": matches, "query": query},
#         )
#     return HttpResponse("<p class='error'>Invalid request method</p>", status=400)


# def kpi_dashboard(request, pk):
#     # gets it from urls.py
#     book = Book.objects.get(pk=pk)
#     today = timezone.now().date()
#     start_of_month = today.replace(day=1)

#     # Total balance (all cash accounts)
#     # balance = CashAccount.objects.filter(book=book).aggregate(
#     #     total_balance=Sum("balance")
#     # )["total_balance"] or Decimal("0.00")
#     balance = get_total_base_currency_balance(book_pk=pk)

#     # Transactions for this book between start of month and today
#     transactions = CashTransactionEntry.objects.filter(
#         book=book,
#         created_at__date__gte=start_of_month,
#         created_at__date__lte=today
#     )

#     money_in = sum(t.amount for t in transactions if t.is_amount_positive)
#     money_out = sum(t.amount for t in transactions if not t.is_amount_positive)

#     # Money in and out (all transactions)
#     # money_in = CashTransactionEntry.objects.filter(
#     #     book=book, is_amount_positive=True
#     # ).aggregate(total_in=Sum("amount"))["total_in"] or Decimal("0.00")

#     # money_out = CashTransactionEntry.objects.filter(
#     #     book=book, is_amount_positive=False
#     # ).aggregate(total_out=Sum("amount"))["total_out"] or Decimal("0.00")

#     # Burn = Money Out - Money In (or just Money Out if you prefer)

#     burn = money_out - money_in
#     avg_burn = 5000 #usd per month
#     # Runway = balance / burn (months), avoid division by zero
#     runway = (
#         (balance / avg_burn ).quantize(Decimal("0.1")) if avg_burn > 0 else None
#     )

#     # Growth rate (optional, example: (balance + money_in) / balance)
#     growth_rate = (
#         ((balance + money_in) / balance * 100 - 100).quantize(Decimal("0.1"))
#         if balance > 0
#         else None
#     )

#     # Default alive = True if balance > 0
#     default_alive = balance > 0

#     context = {
#         "balance": balance,
#         "money_in": money_in,
#         "money_out": money_out,
#         "burn": burn,
#         "runway": runway,
#         "growth_rate": growth_rate,
#         "default_alive": default_alive,
#     }

#     return render(request, "accounting/kpi_dashboard.html", context)


# ============================================================================
# SALES DASHBOARD VIEW - Modern order listing with profit calculation
# ============================================================================
from operating.models import Order, OrderItem
from django.core.paginator import Paginator


@method_decorator(login_required, name="dispatch")
class SalesDashboardView(View):
    """Modern sales dashboard showing orders with revenue, cost, and profit."""
    
    template_name = "accounting/sales_dashboard.html"
    
    def get(self, request):
        # Get filter parameters
        days_filter = request.GET.get('days', '365')  # Default to 1 year
        search_query = request.GET.get('search', '').strip()
        page = request.GET.get('page', 1)
        
        # Calculate date range
        try:
            days = int(days_filter)
        except ValueError:
            days = 365
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Base queryset - orders with original_price (web orders)
        orders = Order.objects.filter(
            created_at__gte=start_date,
            original_price__isnull=False
        ).exclude(
            payment_status='failed'
        ).select_related('web_client').prefetch_related(
            'items__product', 'items__product_variant'
        ).order_by('-created_at')
        
        # Search filter by customer name
        if search_query:
            orders = orders.filter(
                Q(web_client__name__icontains=search_query) |
                Q(web_client__username__icontains=search_query) |
                Q(guest_first_name__icontains=search_query) |
                Q(guest_last_name__icontains=search_query) |
                Q(order_number__icontains=search_query)
            )
        
        # Calculate totals and build order list with profit
        total_revenue = Decimal('0')
        total_cost = Decimal('0')
        order_list = []
        
        for order in orders:
            # Get customer name
            if order.web_client:
                customer_name = order.web_client.name or order.web_client.username or "Unknown"
            elif order.guest_first_name or order.guest_last_name:
                customer_name = f"{order.guest_first_name or ''} {order.guest_last_name or ''}".strip()
            else:
                customer_name = "Unknown Customer"
            
            # Calculate order revenue, cost, and profit from items
            order_revenue = Decimal('0')
            order_profit = Decimal('0')
            
            for item in order.items.all():
                qty = item.quantity or Decimal('1')
                # Rounded per line, like OrderItem.subtotal(), so this
                # report's revenue matches the order pages to the cent.
                item_revenue = (item.price * qty).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                order_revenue += item_revenue
                
                # Calculate profit based on item type
                item_profit = Decimal('0')
                
                # Get variant cost and price
                variant_cost = Decimal('0')
                variant_price = Decimal('0')
                
                if item.product_variant:
                    variant_cost = item.product_variant.variant_cost or Decimal('0')
                    variant_price = item.product_variant.variant_price or Decimal('0')
                elif item.product:
                    variant_cost = item.product.cost or Decimal('0')
                    variant_price = item.product.price or Decimal('0')
                
                if item.is_custom_curtain:
                    # Custom Curtain Formula:
                    # Profit = Total Price - (Fabric Amount × (variant_cost + 1)) - (Total Price × 0.145)
                    # Where:
                    #   - Total Price = item.price × quantity
                    #   - Fabric Amount = custom_fabric_used_meters
                    #   - variant_cost + 1 = fabric cost + labor/overhead per meter
                    #   - 0.145 = 14.5% commission (payment processor/marketplace fee)
                    fabric_amount = item.custom_fabric_used_meters or Decimal('0')
                    fabric_cost_with_labor = fabric_amount * (variant_cost + Decimal('1'))
                    commission = item_revenue * Decimal('0.145')
                    item_profit = item_revenue - fabric_cost_with_labor - commission
                else:
                    # Standard Item: Profit = Quantity * (Sold Price - Cost)
                    # Sold Price is item.price
                    unit_margin = item.price - variant_cost
                    item_profit = qty * unit_margin
                
                order_profit += item_profit
            
            # Derive cost from Revenue and Profit to ensure consistency (Revenue - Cost = Profit)
            # Cost = Revenue - Profit
            order_cost = order_revenue - order_profit
            
            total_revenue += order_revenue
            total_cost += order_cost
            
            order_list.append({
                'id': order.id,
                'order_number': order.order_number or f"ORD-{order.id}",
                'customer_name': customer_name or "Unknown",
                'date': order.order_date or order.created_at.date(),
                'revenue': order_revenue,
                'cost': order_cost,
                'profit': order_profit,
                'status': order.order_status or order.payment_status or 'pending',
                'payment_status': order.payment_status,
            })
        
        total_profit = total_revenue - total_cost
        order_count = len(order_list)
        
        # Paginate
        paginator = Paginator(order_list, 20)  # 20 per page
        page_obj = paginator.get_page(page)
        
        # Period stats
        week_ago = end_date - timedelta(days=7)
        month_ago = end_date - timedelta(days=30)
        
        week_revenue = sum(
            o['revenue'] for o in order_list 
            if o['date'] >= week_ago
        )
        month_revenue = sum(
            o['revenue'] for o in order_list 
            if o['date'] >= month_ago
        )
        
        context = {
            'orders': page_obj,
            'page_obj': page_obj,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'order_count': order_count,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'year_revenue': total_revenue,
            'days_filter': days_filter,
            'search_query': search_query,
        }
        
        # Return partial template for HTMX requests
        if request.headers.get('HX-Request'):
            return render(request, 'accounting/partials/sales_content.html', context)
        
        return render(request, self.template_name, context)
