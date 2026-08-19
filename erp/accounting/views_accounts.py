"""
Current account (Cari Hesap) views — Phase 1.

    /accounting/accounts/                     → CariList
    /accounting/accounts/new/                 → CariCreate
    /accounting/accounts/<id>/                → CariDetail    (summary + tabs)
    /accounting/accounts/<id>/statement/      → CariStatement (ekstre)
    /accounting/accounts/<id>/edit/           → CariEdit
    /accounting/accounts/<id>/delete/         → CariDelete
    /accounting/accounts/<id>/movements/new/  → CariMovementCreate (manual entry)
    /accounting/accounts/<id>/movements/<mid>/edit/    → CariMovementEdit
    /accounting/accounts/<id>/movements/<mid>/delete/  → CariMovementDelete (POST)
"""
import json
import re
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


def _movement_choices_including(current):
    """The dropdown for an EXISTING row: the normal choices, plus the
    row's own type when that isn't one we offer (an opening balance, a
    legacy marker). Keeps editing a description from quietly re-typing
    the movement."""
    choices = _user_movement_choices()
    if current and current not in {v for v, _l in choices}:
        label = dict(CariMovement.MOVEMENT_TYPES).get(current, current)
        choices = [(current, label)] + choices
    return choices


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


def _filter_caris(request, apply_type=True):
    """Filtered account queryset.

    apply_type=False leaves the type filter off so the tab counts can be
    computed against everything else the user has narrowed to. A tab needs to
    answer "how many would I get if I clicked this", which is the current
    search, book, balance and active filters — but its own type, not the one
    already selected.
    """
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
    if apply_type and type_filter in dict(CariAccount.TYPE_CHOICES):
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

    # Default (no param) = active only; "0" = inactive only; "all" = both.
    # "all" is an explicit value on purpose — an empty one is stripped from
    # the fetch URL client-side and would silently fall back to the default.
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
    # "id" tiebreaker: the sort fields aren't unique (duplicate names,
    # NULL last_movement_at, equal balances), and without a total order
    # Postgres may return the SAME row on two different pages while
    # another never appears at all.
    qs = qs.order_by(sort_map.get(sort, "name"), "id")
    return qs


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariList(View):
    template_name = "accounts/cari_list.html"

    def get(self, request):
        qs = _filter_caris(request)

        # Aggregate totals across the filtered set (positive vs negative legs)
        totals = qs.aggregate(
            n=Count("id"),
            owes_us=Sum("cached_balance_base", filter=Q(cached_balance__gt=0)),
            we_owe=Sum("cached_balance_base", filter=Q(cached_balance__lt=0)),
        )

        # One count per tab. Previously a single badge sat on the "All" tab and
        # the fetch handler wrote the FILTERED count into it, so selecting
        # Supplier left "All" reading the supplier count. Each tab now carries
        # its own, counted with every filter except type applied.
        untyped = _filter_caris(request, apply_type=False)
        # .order_by() clears the sort before grouping. _filter_caris orders by
        # name and id, and Django folds ordering fields into the GROUP BY — so
        # without this the aggregate groups by (type, name, id) and every count
        # comes back as 1.
        per_type = dict(untyped.order_by().values_list("type")
                        .annotate(n=Count("id")))
        all_count = untyped.count()
        # (value, label, count) so the template can just iterate — a template
        # cannot index a dict by a loop variable without a custom filter.
        type_tabs = [(val, label, per_type.get(val, 0))
                     for val, label in CariAccount.TYPE_CHOICES]
        tab_counts = {"": all_count}
        tab_counts.update({val: n for val, _l, n in type_tabs})

        # Paginate — stats above stay whole-filtered-set; only the rows page.
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        paginator = Paginator(qs, 50)
        try:
            page = paginator.page(request.GET.get("page") or 1)
        except (EmptyPage, PageNotAnInteger):
            page = paginator.page(1)

        ctx = {
            "caris":          page.object_list,
            "page":           page,
            "paginator":      paginator,
            "total_count":    totals["n"] or 0,
            "owes_us":        totals["owes_us"] or Decimal("0.00"),
            "we_owe":         abs(totals["we_owe"] or Decimal("0.00")),
            "net":            (totals["owes_us"] or Decimal("0.00")) + (totals["we_owe"] or Decimal("0.00")),
            "books":          _books(),
            "type_choices":   CariAccount.TYPE_CHOICES,
            "all_count":      all_count,
            "type_tabs":      type_tabs,
            "tab_counts_json": json.dumps(tab_counts),
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
            return render(request, "accounts/partials/cari_list_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create / Edit
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariCreate(View):
    template_name = "accounts/cari_form.html"

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
        from .services_accounts import (
            get_or_create_cari_for_company,
            get_or_create_cari_for_contact, get_or_create_cari_for_supplier,
        )

        entity_type = request.POST.get("entity_type", "company")
        if entity_type not in self.ENTITY_TYPES:
            entity_type = "company"

        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, _g("Name is required."))
            return redirect("accounts:create")

        currency_id = request.POST.get("default_currency")
        if not currency_id:
            messages.error(request, _g("Currency is required."))
            return redirect("accounts:create")

        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("billing_address", "").strip()
        country = request.POST.get("billing_country", "TR").strip()
        member = getattr(request.user, "member", None)

        try:
            if entity_type == "company":
                if Company.objects.filter(name__iexact=name).exists():
                    messages.error(request, _g("A company with this name already exists."))
                    return redirect("accounts:create")
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
            return redirect("accounts:create")

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
            return redirect("accounts:create")
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
        return redirect("accounts:detail", pk=cari.pk)


@method_decorator(login_required, name="dispatch")
class CariEdit(View):
    template_name = "accounts/cari_form.html"

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
        return redirect("accounts:detail", pk=cari.pk)


def _movement_owner(mv, linked_payment=None, linked_invoice=None, is_cancel_row=False):
    """Which document OWNS this ledger row, and where it is edited.

    A movement posted by a payment, an invoice or an order is not an
    entry anyone should edit in place: those documents recompute it
    (Payment.resync_posted_movement, Invoice.resync_posted_movement,
    post_order_movement), so a hand-edit here is overwritten the next
    time the document is touched — silently, and only sometimes. Such a
    row therefore sends the user to the document instead.

    Returns (label, url, editable_here). A manual movement — opening
    balance, adjustment, interest, discount — owns itself, and that is
    the only kind this app edits directly.
    """
    if is_cancel_row:
        # Half of a cancellation pair. Reversing a cancellation is not an
        # edit; it is a new document.
        return _("Cancellation record"), None, False
    if linked_payment is not None:
        return (_("Collection / Payment"),
                reverse("accounts:payment_edit", args=[linked_payment.pk]), False)
    if linked_invoice is not None:
        return (_("Invoice"),
                reverse("accounts:invoice_edit", args=[linked_invoice.pk]), False)
    if mv.source_id and mv.source_type_id:
        model = mv.source_type.model_class()
        if model is not None and model.__name__ == "Order":
            return (_("Order"),
                    reverse("operating:order_detail", args=[mv.source_id]), False)
        # Some other document we don't have a route for — still not ours
        # to edit, since whatever posted it can repost it.
        return _("Linked document"), None, False
    return None, None, True


def _row_description(mv, linked_payment=None, linked_invoice=None, is_cancel_row=False):
    """The text the Description column should print for this ledger row.

    A movement posted by a document gets an auto-generated description
    ("Tahsilat — COL-2026-000001", "Satis Faturasi FTR-2026-000004"),
    which is the Type column and the Reference column read back to the
    user a second time. So for those rows print what the *document*
    says instead: the note whoever entered the payment actually typed.
    Nothing to say is better than saying the number again, so when the
    document carries no text of its own the cell stays empty.

    Only a hand-entered movement — opening balance, adjustment, interest
    — has a description that is genuinely its own, and that one is
    printed as written.
    """
    if is_cancel_row:
        # "CANCEL — Tahsilat COL-2026-000001 (reason)". The reason is
        # the only part that isn't already on the row; without it the
        # row would read as a plain adjustment, so keep a label.
        reason = re.search(r"\(([^()]*)\)\s*$", mv.description or "")
        reason = reason.group(1).strip() if reason else ""
        return "%s — %s" % (_("Cancellation"), reason) if reason else _("Cancellation")
    if linked_payment is not None:
        return (linked_payment.description or "").strip()
    if linked_invoice is not None:
        # Invoices have no description of their own — only internal
        # notes, which are not for the statement.
        return ""
    return (mv.description or "").strip()


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
        r["description"] = _row_description(mv, linked_pay, linked_inv, is_cancel)

        owner_label, owner_url, editable = _movement_owner(
            mv, linked_pay, linked_inv, is_cancel)
        r["owner_label"] = owner_label
        r["owner_edit_url"] = owner_url
        r["editable"] = editable
        r["edit_url"] = (
            reverse("accounts:movement_edit", args=[mv.cari_id, mv.pk])
            if editable else owner_url
        )
    return rows


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
class RetailCariRedirect(View):
    """Jump to the shared walk-in sales account.

    Retail used to have a defter of its own (a "Perakende" Book with its
    own till and EquityRevenue rows) alongside this cari, which recorded
    every walk-in sale twice in two places that drifted apart. The book
    is gone; the PERAKENDE cari is the single retail record, so the
    nav's "Perakende Satışları" entry lands here.

    Resolved by code rather than a hardcoded pk because each brand runs
    its own schema — cari 17 on demfirat is not cari 17 on another brand.
    """

    def get(self, request):
        from accounting.services_accounts import (
            RETAIL_CARI_CODE, get_or_create_retail_cari,
        )

        cari = CariAccount.objects.filter(code=RETAIL_CARI_CODE).first()
        if not cari:
            # Nothing sold at the counter yet — create the account so the
            # link never dead-ends on a fresh install.
            cari = get_or_create_retail_cari(
                member=getattr(request.user, "member", None))
        return redirect("accounts:detail", pk=cari.pk)


class CariDetail(View):
    template_name = "accounts/cari_detail.html"

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
        # cached_balance is a base-currency (USD) figure, so the walk back
        # through it has to use amount_base too — subtracting a raw EUR
        # `amount` from a USD balance is what made these columns disagree.
        running = cari.cached_balance
        for mv in recent_movements:
            movements_with_balance.append({"mv": mv, "balance_after": running})
            running -= mv.amount_base
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
    template_name = "accounts/cari_statement.html"

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
        # Base currency throughout — see CariAccount.recompute_balance.
        opening = prior_qs.aggregate(s=Sum("amount_base"))["s"] or Decimal("0.00")
        running = opening

        for mv in qs:
            running += mv.amount_base
            rows.append({"mv": mv, "balance_after": running})
        _attach_links(rows)

        # Reading order is a DISPLAY choice, made after the walk. The
        # query itself has to stay oldest-first whatever the user picks:
        # every row's balance is the opening balance plus everything
        # before it, so computing it backwards would print a different
        # number on every line.
        sort = "desc" if request.GET.get("sort") == "desc" else "asc"

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

        if sort == "desc":
            rows = list(reversed(rows))

        ctx = {
            "cari":         cari,
            "rows":         rows,
            "sort":         sort,
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
            return render(request, "accounts/_cari_statement_results.html", ctx)
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# All-accounts printable statement — every cari's CURRENT balance, split
# into who owes us (borçlular) vs who we owe (alacaklılar) so each side
# can be printed on its own.
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariStatementAll(View):
    template_name = "accounts/cari_statement_all.html"

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
    template_name = "accounts/movement_form.html"

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
            return redirect("accounts:movement_create", pk=cari.pk)

        if amount == 0:
            messages.error(request, _g("Amount cannot be zero."))
            return redirect("accounts:movement_create", pk=cari.pk)

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
        return redirect("accounts:detail", pk=cari.pk)


# ---------------------------------------------------------------------------
# Movement edit / delete — hand-entered rows only
# ---------------------------------------------------------------------------
def _own_movement_or_redirect(request, cari, mv_pk):
    """Fetch a movement of THIS account and refuse it if a document owns
    it. Enforced server-side, not just by hiding the pencil: a typed or
    bookmarked URL must not be able to edit a row that a payment,
    invoice or order will recompute anyway.

    Returns (movement, None) or (None, redirect_response).
    """
    mv = get_object_or_404(CariMovement, pk=mv_pk, cari=cari)
    rows = _attach_links([{"mv": mv, "balance_after": Decimal("0")}])
    row = rows[0]
    if row["editable"]:
        return mv, None

    label = row["owner_label"]
    if row["owner_edit_url"]:
        messages.info(request,
                      _g("This row belongs to a %(doc)s — edit it there and the "
                         "statement follows.") % {"doc": label})
        return None, redirect(row["owner_edit_url"])
    messages.warning(request,
                     _g("This row belongs to a %(doc)s and can't be edited "
                        "from the statement.") % {"doc": label})
    return None, redirect("accounts:statement", pk=cari.pk)


@method_decorator(login_required, name="dispatch")
class CariMovementEdit(View):
    """Edit a hand-entered ledger row — an opening balance, an
    adjustment, interest, a discount.

    Amount, direction, date, currency, type and the free text are all
    fair game. Saving re-derives the account balance (CariMovement.save)
    and refreshes the legacy AR/AP mirror through the same post_save
    signal that created it.
    """
    template_name = "accounts/movement_form.html"

    def get(self, request, pk, mv_pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        mv, blocked = _own_movement_or_redirect(request, cari, mv_pk)
        if blocked:
            return blocked
        return render(request, self.template_name, {
            "cari": cari,
            "movement": mv,
            # The form asks for a magnitude plus a debit/credit radio;
            # the stored amount carries the sign.
            "abs_amount": abs(mv.amount),
            # The stored type can be one we never offer in the dropdown
            # (an "opening" row, a legacy marker). Add it rather than
            # silently re-typing the row on the first save.
            "movement_type_choices": _movement_choices_including(mv.movement_type),
            "currencies": _currencies(),
        })

    def post(self, request, pk, mv_pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        mv, blocked = _own_movement_or_redirect(request, cari, mv_pk)
        if blocked:
            return blocked

        try:
            amount = Decimal(request.POST.get("amount") or "0")
        except Exception:
            messages.error(request, _g("Invalid amount."))
            return redirect("accounts:movement_edit", pk=cari.pk, mv_pk=mv.pk)
        if amount == 0:
            messages.error(request, _g("Amount cannot be zero."))
            return redirect("accounts:movement_edit", pk=cari.pk, mv_pk=mv.pk)

        direction = request.POST.get("direction") or "debit"
        mv.amount = abs(amount) if direction == "debit" else -abs(amount)
        # amount_base is what the balance is summed from, and
        # CariMovement.save() only recomputes it when it is falsy —
        # leaving it as-is would save a new amount that never reached
        # the balance.
        mv.amount_base = Decimal("0")
        mv.date = request.POST.get("date") or mv.date
        mv.due_date = request.POST.get("due_date") or None
        currency_id = request.POST.get("currency")
        if currency_id:
            mv.currency_id = int(currency_id)

        movement_type = request.POST.get("movement_type") or mv.movement_type
        # Same supplier normalisation as the create form — the dropdown
        # only ever shows "collection".
        if movement_type == "collection" and cari.type == "supplier":
            movement_type = "payment"
        mv.movement_type = movement_type

        mv.description = request.POST.get("description", "")
        mv.reference = request.POST.get("reference", "")
        mv.save()   # recomputes amount_base + the account balance

        messages.success(request, _g("Movement updated."))
        return redirect("accounts:statement", pk=cari.pk)


@method_decorator(login_required, name="dispatch")
class CariMovementDelete(View):
    """Delete a hand-entered ledger row. The post_delete signal drops the
    legacy AR/AP mirror and recomputes the balance."""

    def post(self, request, pk, mv_pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        mv, blocked = _own_movement_or_redirect(request, cari, mv_pk)
        if blocked:
            return blocked
        mv.delete()
        messages.success(request, _g("Movement deleted."))
        return redirect("accounts:statement", pk=cari.pk)


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
        return redirect("accounts:list")
