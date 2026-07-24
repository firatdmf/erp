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
from .models import CariAccount, CariMovement, CariSettings, Payment, Invoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _books():
    return Book.objects.all().order_by("name")


def _currencies():
    return CurrencyCategory.objects.all().order_by("code")


# Movement types we expose to the user in dropdowns. We deliberately
# strip:
# - legacy_ar / legacy_ap → internal migration markers, never user-picked
# - payment              → consolidated under "collection"; cari.type
#                          decides direction at save time, so the user
#                          only ever sees ONE "Tahsilat" option
# - check_in / check_out → handled by the dedicated Check/Note form
#                          (Quick Actions → "Check / Note"), no point
#                          duplicating them in the generic dropdown
_HIDDEN_MOVEMENT_TYPES = {"legacy_ar", "legacy_ap", "payment", "check_in", "check_out"}

def _user_movement_choices():
    return [(v, l) for v, l in CariMovement.MOVEMENT_TYPES if v not in _HIDDEN_MOVEMENT_TYPES]


def _tr_case_variants(q):
    """Query variants that make search genuinely case-insensitive for
    TURKISH text. SQL ILIKE only folds ASCII (i↔I): typing lowercase
    'kızılırmak' never matches the stored uppercase 'KIZILIRMAK'
    because dotless 'ı' ↔ 'I' (and dotted 'i' ↔ 'İ') aren't in the
    fold. We OR the original with Turkish-aware upper/lower versions
    so any casing the user types finds any casing in the DB."""
    tr_upper = q.replace("i", "İ").replace("ı", "I").upper()
    tr_lower = q.replace("İ", "i").replace("I", "ı").lower()
    return {q, tr_upper, tr_lower}


def _filter_caris(request):
    qs = CariAccount.objects.select_related("book", "default_currency").all()

    q = (request.GET.get("q") or "").strip()
    if q:
        cond = Q()
        for v in _tr_case_variants(q):
            cond |= (
                Q(code__icontains=v)
                | Q(name__icontains=v)
                | Q(tax_number__icontains=v)
                | Q(email__icontains=v)
                | Q(phone__icontains=v)
            )
        qs = qs.filter(cond)

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
        # Dynamic search/filter: the page JS fetches with this header and
        # swaps ONLY the results block — no full page reload per keystroke.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(request, "current_account/partials/cari_list_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create / Edit
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariCreate(View):
    template_name = "current_account/cari_form.html"

    ENTITY_TYPES = ("company", "contact", "supplier")

    def get(self, request):
        return render(request, self.template_name, {
            "cari": None,
            "books": _books(),
            "currencies": _currencies(),
            "type_choices": CariAccount.TYPE_CHOICES,
            "entity_types": self.ENTITY_TYPES,
        })

    def post(self, request):
        # A cari is never a floating record any more — creating one here
        # always creates the matching CRM entity (company/contact) or
        # Supplier alongside it (the same "supplier gets a cari" rule
        # applied uniformly), so there's one job instead of two.
        from crm.models import Company, Contact, Supplier
        from .services import (
            get_or_create_cari_for_company,
            get_or_create_cari_for_contact, get_or_create_cari_for_supplier,
        )

        entity_type = request.POST.get("entity_type", "company")
        if entity_type not in self.ENTITY_TYPES:
            entity_type = "company"

        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, _g("Name is required."))
            return redirect("current_account:cari_create")

        currency_id = request.POST.get("default_currency")
        if not currency_id:
            messages.error(request, _g("Currency is required."))
            return redirect("current_account:cari_create")

        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("billing_address", "").strip()
        country = request.POST.get("billing_country", "TR").strip()
        member = getattr(request.user, "member", None)

        try:
            if entity_type == "company":
                if Company.objects.filter(name__iexact=name).exists():
                    messages.error(request, _g("A company with this name already exists."))
                    return redirect("current_account:cari_create")
                entity = Company.objects.create(
                    name=name,
                    email=[email] if email else [],
                    phone=[phone] if phone else [],
                    address=address,
                    country=country,
                )
                cari = get_or_create_cari_for_company(entity, member=member)
            elif entity_type == "contact":
                entity = Contact.objects.create(
                    name=name,
                    email=[email] if email else [],
                    phone=[phone] if phone else [],
                    address=address,
                    country=country,
                )
                cari = get_or_create_cari_for_contact(entity, member=member)
            else:
                entity = Supplier.objects.create(
                    company_name=name,
                    email=email, phone=phone,
                    address=address, country=country,
                )
                # The post_save signal on Supplier already creates the
                # cari unconditionally — this call is idempotent and
                # just fetches that same row.
                cari = get_or_create_cari_for_supplier(entity, member=member)
        except Exception as exc:
            messages.error(request, _g("Could not create record: %(error)s") % {"error": exc})
            return redirect("current_account:cari_create")

        # Layer the cari-specific commercial/tax fields on top of the
        # row the service function just created.
        cari.default_currency_id = int(currency_id)
        cari.payment_term_days = int(request.POST.get("payment_term_days") or 30)
        cari.credit_limit = Decimal(request.POST.get("credit_limit") or "0")
        cari.discount_rate = Decimal(request.POST.get("discount_rate") or "0")
        cari.tax_office = request.POST.get("tax_office", "")
        cari.tax_number = request.POST.get("tax_number", "")
        cari.identity_number = request.POST.get("identity_number", "")
        cari.billing_address = address
        cari.billing_city = request.POST.get("billing_city", "")
        cari.billing_country = country
        cari.email = email
        cari.phone = phone
        cari.notes = request.POST.get("notes", "")
        opening_balance = Decimal(request.POST.get("opening_balance") or "0")
        cari.opening_balance = opening_balance
        cari.opening_balance_date = request.POST.get("opening_balance_date") or None

        try:
            cari.full_clean(exclude=["code"])
        except Exception as exc:
            messages.error(request, _g("Invalid data: %(error)s") % {"error": exc})
            return redirect("current_account:cari_create")
        cari.save()

        # If opening balance non-zero, drop a single opening movement
        if opening_balance and opening_balance != Decimal("0"):
            CariMovement.objects.create(
                cari=cari,
                book=cari.book,
                date=cari.opening_balance_date or timezone.now().date(),
                amount=opening_balance,
                currency=cari.default_currency,
                movement_type="opening",
                description="Opening balance",
                created_by=member,
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


def _attach_links(rows):
    """Annotate each {'mv': ..., 'balance_after': ...} row with the
    Payment/Invoice it relates to and whether it is the cancellation
    counter-movement (so the template can avoid double-stamping the
    CANCELLED badge on the original row)."""
    from django.contrib.contenttypes.models import ContentType
    pay_ct = ContentType.objects.get_for_model(Payment)
    inv_ct = ContentType.objects.get_for_model(Invoice)

    # Pre-fetch all Payment/Invoice rows referenced via the generic
    # source FK (one query each, not N).
    cancel_pay_ids = [
        r["mv"].source_id for r in rows
        if r["mv"].movement_type == "adjustment"
        and r["mv"].source_type_id == pay_ct.id and r["mv"].source_id
    ]
    cancel_inv_ids = [
        r["mv"].source_id for r in rows
        if r["mv"].movement_type == "adjustment"
        and r["mv"].source_type_id == inv_ct.id and r["mv"].source_id
    ]
    pay_map = {p.pk: p for p in Payment.objects.filter(pk__in=cancel_pay_ids)} if cancel_pay_ids else {}
    inv_map = {i.pk: i for i in Invoice.objects.filter(pk__in=cancel_inv_ids)} if cancel_inv_ids else {}

    for r in rows:
        mv = r["mv"]
        linked_pay = None
        linked_inv = None
        is_cancel = False

        # 1) Originals — Payment.posted_movement (OneToOne reverse).
        try:
            linked_pay = mv.payment
        except Payment.DoesNotExist:
            linked_pay = None
        if linked_pay is None:
            try:
                linked_inv = mv.invoice
            except Invoice.DoesNotExist:
                linked_inv = None

        # 2) Cancellation counter-movements — generic FK source.
        if not linked_pay and not linked_inv and mv.movement_type == "adjustment" and mv.source_id:
            if mv.source_type_id == pay_ct.id:
                linked_pay = pay_map.get(mv.source_id)
                is_cancel = bool(linked_pay)
            elif mv.source_type_id == inv_ct.id:
                linked_inv = inv_map.get(mv.source_id)
                is_cancel = bool(linked_inv)

        r["linked_payment"] = linked_pay
        r["linked_invoice"] = linked_inv
        r["is_cancel_row"] = is_cancel
    return rows


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
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
            .select_related("currency", "created_by__user")
            .order_by("-date", "-id")[:20]
        )
        movements_with_balance = []
        running = cari.cached_balance
        for mv in recent_movements:
            movements_with_balance.append({"mv": mv, "balance_after": running})
            running -= mv.amount
        _attach_links(movements_with_balance)

        recent_invoices = cari.invoices.select_related("currency").order_by("-date", "-id")[:10]

        # Orders attached to this cari — newest first. Items prefetched
        # so gross_profit() can run cheaply in the template if needed.
        recent_orders = (
            cari.orders.select_related("contact", "company", "web_client")
            .prefetch_related("items__product", "items__product_variant")
            .order_by("-created_at")[:20]
        )

        ctx = {
            "cari":     cari,
            "movements": movements_with_balance,
            "recent_invoices": recent_invoices,
            "recent_orders": recent_orders,
            "movement_type_choices": _user_movement_choices(),
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
        from django.contrib.contenttypes.models import ContentType

        cari = get_object_or_404(CariAccount, pk=pk)

        # ── Filters from query string ──────────────────────────────
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or ""
        direction = (request.GET.get("direction") or "").strip()   # in / out
        status_f  = (request.GET.get("status") or "").strip()      # cancelled

        # Cancellation predicate — match BOTH halves of each cancel pair:
        #   (a) the counter-CANCEL adjustment row (source FK + CANCEL
        #       prefix in description/reference)
        #   (b) the ORIGINAL payment/invoice row, whichever way it's
        #       linked. Two link paths exist for historical reasons:
        #       - source_type/source_id FK (set by Payment.confirm)
        #       - posted_movement OneToOne reverse (`mv.payment` /
        #         `mv.invoice`) — present even when the source FK was
        #         never populated (e.g. movements added via the
        #         "Add Movement" form that the signal then mirrored
        #         into a Payment).
        # Without the reverse-FK leg, cancelled collections added via
        # the manual form leak into Girişler.
        pay_ct = ContentType.objects.get_for_model(Payment)
        inv_ct = ContentType.objects.get_for_model(Invoice)
        cancel_counter_q = (
            Q(movement_type="adjustment")
            & Q(source_type__in=[pay_ct, inv_ct])
            & Q(source_id__isnull=False)
            & (Q(reference__startswith="CANCEL") | Q(description__startswith="CANCEL"))
        )
        cancelled_pay_ids = list(Payment.objects.filter(status="cancelled").values_list("pk", flat=True))
        cancelled_inv_ids = list(Invoice.objects.filter(status="cancelled").values_list("pk", flat=True))
        cancelled_original_q = (
            # explicit FK side
            (Q(source_type=pay_ct) & Q(source_id__in=cancelled_pay_ids))
            | (Q(source_type=inv_ct) & Q(source_id__in=cancelled_inv_ids))
            # reverse OneToOne side
            | Q(payment__status="cancelled")
            | Q(invoice__status="cancelled")
        )
        all_cancel_q = cancel_counter_q | cancelled_original_q

        # Base queryset — date range first so the prior-balance
        # calculation stays correct.
        base = cari.movements.select_related("currency", "created_by__user").all()
        qs = base.order_by("date", "id")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Status:
        #   default / direction filters → ACTIVE only (cancelled hidden
        #     from list and totals)
        #   status=cancelled → ONLY cancelled rows
        if status_f == "cancelled":
            qs = qs.filter(all_cancel_q)
        else:
            qs = qs.exclude(all_cancel_q)

        # Direction (only meaningful when status != cancelled):
        if status_f != "cancelled":
            if direction == "in":
                qs = qs.filter(amount__lt=0)
            elif direction == "out":
                qs = qs.filter(amount__gt=0)

        # Walking forward → running balance per row.
        # Opening balance uses prior movements (also excluding
        # cancelled, so the live ledger stays consistent).
        rows = []
        prior_qs = base
        if date_from:
            prior_qs = prior_qs.filter(date__lt=date_from)
        else:
            prior_qs = prior_qs.none()
        if status_f != "cancelled":
            prior_qs = prior_qs.exclude(all_cancel_q)
        opening = prior_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        running = opening

        for mv in qs:
            running += mv.amount
            rows.append({"mv": mv, "balance_after": running})
        _attach_links(rows)

        # Totals match the filtered rows. For cancelled-only view this
        # naturally shows the cancelled amount (debit/credit both sum
        # since each cancellation has +X and -X) and closing = 0.
        debit_total = Decimal("0.00")
        credit_total = Decimal("0.00")
        for r in rows:
            mv = r["mv"]
            if mv.amount > 0:
                debit_total += mv.amount
            else:
                credit_total += abs(mv.amount)

        ctx = {
            "cari":         cari,
            "rows":         rows,
            "opening":      opening,
            "closing":      running,
            "debit_total":  debit_total,
            "credit_total": credit_total,
            "date_from":    date_from,
            "date_to":      date_to,
            "filter_direction": direction,
            "filter_status":    status_f,
        }
        # HTMX partial — when the filter bar fires, swap only the
        # results region instead of re-rendering the whole page.
        if request.headers.get("HX-Request") == "true":
            return render(request, "current_account/_cari_statement_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# All-accounts printable statement — every cari's CURRENT balance, split
# into who owes us (borçlular) vs who we owe (alacaklılar) so each side
# can be printed on its own.
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariStatementAll(View):
    template_name = "current_account/cari_statement_all.html"

    def get(self, request):
        caris = (
            CariAccount.objects.filter(is_active=True)
            .select_related("book", "default_currency")
            .exclude(cached_balance=0)
            .order_by("-cached_balance")
        )
        debtors = [c for c in caris if c.cached_balance > 0]     # owe US
        creditors = [c for c in caris if c.cached_balance < 0]   # WE owe them

        creditors_total = sum((c.cached_balance for c in creditors), Decimal("0.00"))
        return render(request, self.template_name, {
            "debtors": debtors,
            "creditors": creditors,
            "debtors_total": sum((c.cached_balance for c in debtors), Decimal("0.00")),
            "creditors_total": abs(creditors_total),
            "generated_at": timezone.now(),
        })


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
            "movement_type_choices": _user_movement_choices(),
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

        # The user always picks "Tahsilat" (collection) in the dropdown,
        # because we hide "payment". For supplier accounts, money moving
        # this direction is semantically a PAYMENT (we're paying them),
        # so normalise here. Keeps Payment.type accurate downstream and
        # the tahsilat list labels match reality.
        if movement_type == "collection" and cari.type == "supplier":
            movement_type = "payment"

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

        # Payment mirror (collection / payment types) is handled by the
        # post_save signal on CariMovement — see signals.py. That way
        # any code path that creates such a movement automatically
        # gets a matching Payment, not just this view.
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
