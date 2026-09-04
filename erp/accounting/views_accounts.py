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

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import Book, CurrencyCategory
from .models import (
    CariAccount, CariMovement, CariSettings, CariTransfer, Payment, Invoice,
)
from .forms import CariTransferForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _books():
    return Book.objects.all().order_by("name")


def _member_books(request):
    """The books this reader may switch to — never the full list.

    A book they cannot open has no business appearing in a picker that
    would only 404 them.
    """
    from .services_accounts import member_books
    return member_books(getattr(request.user, "member", None))


def _currencies():
    return CurrencyCategory.objects.all().order_by("code")


# Movement types we expose to the user in dropdowns. We deliberately
# strip:
# - legacy_ar / legacy_ap → internal migration markers, never user-picked
# - check_in / check_out → handled by the dedicated Check/Note form
#                          (Quick Actions → "Check / Note"), no point
#                          duplicating them in the generic dropdown
#
# "collection" and "payment" are both offered: a supplier account picking
# "Collection" is still normalised to "payment" at save time below (so a
# habit formed before "payment" was exposed keeps working), but the user
# can now pick "Payment" directly on any account — e.g. a refund paid out
# to a customer.
_HIDDEN_MOVEMENT_TYPES = {"legacy_ar", "legacy_ap", "check_in", "check_out"}

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


# Turkish letters and the ASCII letter each one folds to.
_TR_FROM = "ıİşŞğĞüÜöÖçÇâÂîÎûÛ"
_TR_TO   = "iIsSgGuUoOcCaAiIuU"


def tr_fold(value):
    """An ASCII, upper-cased form of a string, for comparing names.

    Search has to survive two separate problems at once. SQL's ILIKE
    folds only ASCII case, so 'ı'/'I' and 'i'/'İ' never meet — typing
    'kızılırmak' misses the stored 'KIZILIRMAK'. And people type on
    whatever keyboard they have: 'gurhan' has to find 'GÜRHAN', because
    requiring the reader to produce a Ü before they can look anything up
    is not a search box, it is a quiz.

    Folding both sides to plain uppercase ASCII settles both. The DB side
    is folded in SQL by tr_fold_expr() so no extension or extra column is
    needed.
    """
    return (value or "").translate(str.maketrans(_TR_FROM, _TR_TO)).upper()


def tr_fold_expr(field):
    """The same fold as tr_fold(), applied to a column by Postgres.

    translate() is standard SQL and needs no extension. There is no index
    behind it, which is fine at this size — a book holds low thousands of
    accounts, and the alternative is a denormalised column to keep in
    sync forever.
    """
    from django.db.models import Func, Value
    from django.db.models.functions import Upper
    return Upper(Func(field, Value(_TR_FROM), Value(_TR_TO), function="translate"))


def _tr_case_variants(q):
    """Deprecated — kept so older call sites keep working.

    Superseded by tr_fold()/tr_fold_expr(), which fold both sides once
    instead of guessing at the casings the user might have typed.
    """
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
        needle = tr_fold(q)
        qs = qs.annotate(
            _f_code=tr_fold_expr("code"),
            _f_name=tr_fold_expr("name"),
        ).filter(
            Q(_f_code__contains=needle)
            | Q(_f_name__contains=needle)
            | Q(tax_number__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )

    # The book is not a filter the reader can drop — it is which business
    # the page is about, and it comes from the path. Summing two books'
    # balances into one total was the bug this replaced.
    qs = qs.filter(book=request.book)

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

    # Whether the account stands for a CRM record. Not a tab: it cuts
    # across every type, and the set it names is a backlog to work
    # through rather than a kind of account. Most of the Laleli book came
    # in from the legacy ledger with nothing behind it, so this is the
    # only way to see what is still waiting to be identified.
    crm_filter = request.GET.get("crm") or ""
    unlinked = Q(contact__isnull=True, company__isnull=True, supplier__isnull=True)
    if crm_filter == "none":
        qs = qs.filter(unlinked)
    elif crm_filter == "linked":
        qs = qs.exclude(unlinked)

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


@method_decorator(login_required, name="dispatch")
class LegacyCollectionRedirect(generic.RedirectView):
    """Send a pre-split ledger URL to the same page in the working book.

    /accounting/accounts/ used to list every book at once. It now names a
    book, so the old address has to choose one — and the right choice is
    the same one every other book-less entry point makes: the viewer's
    working book.

    Kept rather than deleted because these URLs are in people's
    bookmarks, in old emails, and in any template not yet moved over.
    """
    permanent = False
    target = None

    def get_redirect_url(self, *args, **kwargs):
        from .services_accounts import get_default_book
        member = getattr(self.request.user, "member", None)
        book = get_default_book(member)
        url = reverse(self.target, kwargs={"book_id": book.pk})
        query = self.request.META.get("QUERY_STRING", "")
        return f"{url}?{query}" if query else url


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
            # Summed and filtered on the SAME column. These used to sum
            # cached_balance_base while filtering on cached_balance — two
            # columns holding one number, correct only for as long as they
            # agreed. The duplicate is gone; there is one balance now.
            owes_us=Sum("cached_balance", filter=Q(cached_balance__gt=0)),
            we_owe=Sum("cached_balance", filter=Q(cached_balance__lt=0)),
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
            "books":          _member_books(request),
            "type_choices":   CariAccount.TYPE_CHOICES,
            "all_count":      all_count,
            "type_tabs":      type_tabs,
            "tab_counts_json": json.dumps(tab_counts),
            "q":              request.GET.get("q", ""),
            "filter_book":    str(request.book.pk),
            "filter_type":    request.GET.get("type", ""),
            "filter_balance": request.GET.get("balance", ""),
            "filter_crm":     request.GET.get("crm", ""),
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
            "books": _member_books(request),
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
            return redirect("accounts:create", book_id=request.book.pk)

        currency_id = request.POST.get("default_currency")
        if not currency_id:
            messages.error(request, _g("Currency is required."))
            return redirect("accounts:create", book_id=request.book.pk)

        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("billing_address", "").strip()
        country = request.POST.get("billing_country", "TR").strip()
        member = getattr(request.user, "member", None)

        try:
            if entity_type == "company":
                if Company.objects.filter(name__iexact=name).exists():
                    messages.error(request, _g("A company with this name already exists."))
                    return redirect("accounts:create", book_id=request.book.pk)
                entity = Company.objects.create(
                    name=name,
                    email=[email] if email else [],
                    phone=[phone] if phone else [],
                    address=address,
                    country=country,
                )
                cari = get_or_create_cari_for_company(
                    entity, member=member, book=request.book)
            elif entity_type == "contact":
                entity = Contact.objects.create(
                    name=name,
                    email=[email] if email else [],
                    phone=[phone] if phone else [],
                    address=address,
                    country=country,
                )
                cari = get_or_create_cari_for_contact(
                    entity, member=member, book=request.book)
            else:
                entity = Supplier.objects.create(
                    company_name=name,
                    email=email, phone=phone,
                    address=address, country=country,
                )
                # The post_save signal on Supplier already creates the
                # cari unconditionally — this call is idempotent and
                # just fetches that same row.
                cari = get_or_create_cari_for_supplier(
                    entity, member=member, book=request.book)
        except Exception as exc:
            messages.error(request, _g("Could not create record: %(error)s") % {"error": exc})
            return redirect("accounts:create", book_id=request.book.pk)

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
            return redirect("accounts:create", book_id=request.book.pk)
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
            "books": _member_books(request),
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


# ---------------------------------------------------------------------------
# CRM link
#
# An account is meant to stand for someone the CRM already knows, and
# creating one here always mints the matching record. Nothing did that for
# the accounts carried in from the legacy Laleli ledger, and until now
# nothing could: CariEdit never touched the three link fields, so 1,148
# accounts had no CRM record and no way to be given one short of a shell.
# Downstream code had begun working around the hole rather than closing it
# (warehouse intake reads through cari.supplier, which is empty for every
# imported account).
#
# So: a picker on the account page. Attach an existing record, mint one
# from what the account already knows about itself, or detach a wrong
# guess. One account at a time, by someone who recognises the name —
# there is no fuzzy match to be had here, the imported names ("AHMET
# ABİ", "İNNA GALA KOTOBSK 63 KARGO KOD 3325") overlap the CRM's 224
# companies in exactly zero places.
# ---------------------------------------------------------------------------
# One list, defined on the model beside the fields themselves — this used
# to be spelled out again here, and two copies of "which three FKs" is how
# a fourth would end up honoured in one place and not the other.
_CRM_KINDS = CariAccount.CRM_FIELDS


def _crm_subtitle(obj):
    """A second line for a picker row.

    Enough to tell two records with the same name apart without opening
    either — which is the whole job of this list.
    """
    bits = []
    country = (getattr(obj, "country", "") or "").strip()
    if country:
        bits.append(country)
    email = getattr(obj, "email", None)
    if isinstance(email, list):          # Contact/Company hold an array
        email = email[0] if email else ""
    if email:
        bits.append(email)
    return " · ".join(bits)


def _crm_model(kind):
    from crm.models import Company, Contact, Supplier
    return {"contact": Contact, "company": Company, "supplier": Supplier}[kind]


@method_decorator(login_required, name="dispatch")
class CariCrmSearch(View):
    """Candidate CRM records for the account page's link picker (JSON).

    Matched with the same Turkish fold the account list searches by, so
    "gurhan" finds "GÜRHAN" from a keyboard that cannot type Ü.

    Every candidate says whether it is already spoken for IN THIS BOOK.
    A CRM record holds at most one account per book (the uniq_cari_book_*
    constraints), so offering a taken one could only end in an
    IntegrityError at save time. Naming the account that holds it is more
    useful than hiding it anyway: that account is usually the duplicate
    the reader was about to create by hand.
    """
    LIMIT = 8

    def get(self, request, pk):
        from crm.models import Company, Contact, Supplier

        cari = get_object_or_404(CariAccount, pk=pk)
        q = (request.GET.get("q") or "").strip()
        if not q:
            return JsonResponse({"results": []})
        needle = tr_fold(q)

        found = {
            "contact": list(
                Contact.objects.annotate(_f=tr_fold_expr("name"))
                .filter(_f__contains=needle).order_by("name")[:self.LIMIT]
            ),
            "company": list(
                Company.objects.annotate(_f=tr_fold_expr("name"))
                .filter(_f__contains=needle).order_by("name")[:self.LIMIT]
            ),
            # A supplier is named by whichever of the two columns is
            # filled — __str__ prefers company_name — so both are searched.
            "supplier": list(
                Supplier.objects.annotate(_fc=tr_fold_expr("company_name"),
                                          _fn=tr_fold_expr("contact_name"))
                .filter(Q(_fc__contains=needle) | Q(_fn__contains=needle))
                .order_by("company_name", "contact_name")[:self.LIMIT]
            ),
        }

        results = []
        for kind in _CRM_KINDS:
            rows = found[kind]
            if not rows:
                continue
            # One query per kind, not one per row.
            holders = {
                getattr(c, f"{kind}_id"): c
                for c in CariAccount.objects
                .filter(book=cari.book, **{f"{kind}__in": rows})
                .exclude(pk=cari.pk)
            }
            for obj in rows:
                held = holders.get(obj.pk)
                results.append({
                    "kind": kind,
                    "id": obj.pk,
                    "label": str(obj),
                    "sub": _crm_subtitle(obj),
                    "taken": None if held is None else {
                        "code": held.code,
                        "name": held.name,
                        "url": reverse("accounts:detail", args=[held.pk]),
                    },
                })
        return JsonResponse({"results": results})


@method_decorator(login_required, name="dispatch")
class CariCrmLink(View):
    """Attach the account to a CRM record, mint one for it, or detach it.

    Three actions on one route because they are one decision — who is
    this account? — and splitting them across three URLs would only make
    the redirect and the error handling three times over.
    """

    def post(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        action = (request.POST.get("action") or "").strip()

        if action == "detach":
            if not cari.crm_link_field:
                messages.info(request, _g("This account has no CRM link."))
                return redirect("accounts:detail", pk=cari.pk)
            was = str(cari.crm_link)
            cari.contact = cari.company = cari.supplier = None
            cari.save(update_fields=["contact", "company", "supplier", "updated_at"])
            messages.success(
                request,
                _g("CRM link removed (%(name)s). The account and its ledger are untouched.")
                % {"name": was},
            )
            return redirect("accounts:detail", pk=cari.pk)

        kind = (request.POST.get("kind") or "").strip()
        if kind not in _CRM_KINDS:
            messages.error(request, _g("Pick a contact, company or supplier."))
            return redirect("accounts:detail", pk=cari.pk)

        if action == "create":
            obj = self._create(request, cari, kind)
            if obj is None:
                return redirect("accounts:detail", pk=cari.pk)
        elif action == "attach":
            obj = _crm_model(kind).objects.filter(pk=request.POST.get("id")).first()
            if obj is None:
                messages.error(request, _g("That CRM record no longer exists."))
                return redirect("accounts:detail", pk=cari.pk)
        else:
            messages.error(request, _g("Unknown action."))
            return redirect("accounts:detail", pk=cari.pk)

        # Checked before saving rather than caught afterwards: a
        # constraint violation would say "duplicate key value violates
        # uniq_cari_book_company", and the reader needs the account's
        # code, which is the thing they were actually looking for.
        holder = (CariAccount.objects
                  .filter(book=cari.book, **{kind: obj})
                  .exclude(pk=cari.pk).first())
        if holder is not None:
            messages.error(
                request,
                _g("%(name)s is already linked to account %(code)s (%(account)s) "
                   "in this book. An account and a CRM record go together one "
                   "to one — if these two are the same customer, the balances "
                   "belong on one of them.")
                % {"name": str(obj), "code": holder.code, "account": holder.name},
            )
            return redirect("accounts:detail", pk=cari.pk)

        # Exactly one of the three, always — clean() refuses two, and
        # re-pointing a link has to clear the old one to obey that.
        for field in _CRM_KINDS:
            setattr(cari, field, obj if field == kind else None)
        cari.save(update_fields=[*_CRM_KINDS, "updated_at"])
        messages.success(request, _g("Linked to %(name)s.") % {"name": str(obj)})
        return redirect("accounts:detail", pk=cari.pk)

    def _create(self, request, cari, kind):
        """Mint the CRM record this account has been standing in for.

        Seeded from the account's own fields — the name, address and
        phone on an imported account are the only record of that customer
        anyone has, and retyping them into a CRM form is how they get
        retyped differently.

        Returns the object, or None after reporting why not.
        """
        from crm.models import Company, Contact, Supplier

        name = (request.POST.get("name") or cari.name or "").strip()
        if not name:
            messages.error(request, _g("Name is required."))
            return None

        email = (cari.email or "").strip()
        phone = (cari.phone or "").strip()
        address = (cari.billing_address or "").strip()
        country = (cari.billing_country or "").strip()

        if kind == "company":
            # Company.name is unique, and CariCreate refuses a duplicate
            # rather than quietly reusing the existing row. Same here:
            # attaching to someone else's company because the names match
            # is a judgement only the reader can make, and the search box
            # above this button is how they make it.
            if Company.objects.filter(name__iexact=name).exists():
                messages.error(
                    request,
                    _g("A company named %(name)s already exists — search for it "
                       "above and link to it instead.") % {"name": name},
                )
                return None
            obj = Company(name=name, email=[email] if email else [],
                          phone=[phone] if phone else [],
                          address=address, country=country)
        elif kind == "contact":
            obj = Contact(name=name, email=[email] if email else [],
                          phone=[phone] if phone else [],
                          address=address, country=country)
        else:
            obj = Supplier(company_name=name, email=email, phone=phone,
                           address=address, country=country)

        try:
            # full_clean rather than a silent truncation: Contact.name
            # holds 50 characters and a phone 20, and half the imported
            # account names are longer than that. A name the CRM cannot
            # hold is worth saying out loud — cutting it in half here is
            # how a record becomes unfindable later.
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            messages.error(
                request,
                _g("Could not create the CRM record: %(error)s")
                % {"error": "; ".join(
                    f"{f}: {' '.join(m)}" for f, m in exc.message_dict.items())},
            )
            return None
        return obj


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
        if model is not None and model.__name__ == "EquityExpense":
            # An expense somebody settled on the book's behalf. The expense
            # is what posts this row and what reposts it on every edit, so
            # it is corrected there — and now there is a page to send the
            # user to, which is why this is no longer a dead end. The
            # expense's own page, not its edit form: following a link from
            # a ledger row is asking what this is, not asking to change it.
            return (_("Expense"),
                    reverse("accounting:equity_expense_detail",
                            kwargs={"pk": mv.book_id, "expense_pk": mv.source_id}),
                    False)
        if model is not None and model.__name__ == "CariTransfer":
            # One leg of a pair. Editing it alone would move a balance out
            # of one account without moving it into the other, so the row
            # is read-only here and corrected on the transfer, which
            # rewrites both legs together.
            return (_("Account transfer"),
                    reverse("accounts:transfer_edit", args=[mv.source_id]),
                    False)
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


# ---------------------------------------------------------------------------
# Which rows count is no longer decided here.
#
# This file used to carry _cancelled_movement_q(), which re-derived "is
# this half of a cancelled document's pair?" from the documents on every
# render. The account page did not use it, so the two printed different
# numbers for the same account whenever the excluded set failed to sum to
# zero — which a hard-deleted payment caused, because the CANCEL half was
# matched on reference text that outlived the document while its partner
# was matched on a status that did not.
#
# The answer is now stored on the row as CariMovement.is_void, backfilled
# once by migration 0086, and read through CariMovementQuerySet.live() by
# both the statement and recompute_balance. One rule, one answer.
# ---------------------------------------------------------------------------


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
        # A few more than the 20 shown, because cancelled pairs are
        # dropped below and would otherwise shorten the list.
        recent_movements = (
            cari.movements
            .select_related("currency", "created_by__user")
            .order_by("-date", "-id")[:30]
        )
        movements_with_balance = []
        # cached_balance is a base-currency (USD) figure, so the walk back
        # through it has to use amount_base too — subtracting a raw EUR
        # `amount` from a USD balance is what made these columns disagree.
        running = cari.cached_balance
        for mv in recent_movements:
            movements_with_balance.append({"mv": mv, "balance_after": running})
            running -= mv.amount_base
        # Old cancel pairs read as the same collection listed twice, one
        # of the halves looking live. Dropping AFTER the walk keeps every
        # surviving row's balance the one it actually had, and a pair
        # sums to zero so nothing downstream shifts.
        movements_with_balance = [
            r for r in movements_with_balance if not r["mv"].is_void
        ][:20]
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
            # Buttons on the CRM picker, in the order the CRM itself
            # thinks about people: a person, the firm they work for, then
            # someone we buy from.
            "crm_new_kinds": [
                ("contact",  _("New contact")),
                ("company",  _("New company")),
                ("supplier", _("New supplier")),
            ],
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Statement (Ekstre)
# ---------------------------------------------------------------------------
def _cancelled_documents(cari, date_from="", date_to=""):
    """This account's cancelled documents, for the statement's cancelled view.

    That view filters movements on is_void, and a cancelled INVOICE leaves
    such rows behind. A cancelled PAYMENT does not: Payment.cancel deletes
    the movement outright rather than voiding it, deliberately, so the
    account's history is not padded with a dead line for every correction —
    the record lives on the Payment, which keeps its number and status.

    Which left the page half-answering its own question. Asking for what
    was cancelled returned the invoices and silently omitted the payments,
    with nothing to say the rest existed. The documents are listed here
    beside the rows, so the answer is complete without either of those
    cancellation policies having to change.
    """
    from django.urls import reverse as _reverse

    def _window(qs, field):
        if date_from:
            qs = qs.filter(**{f"{field}__gte": date_from})
        if date_to:
            qs = qs.filter(**{f"{field}__lte": date_to})
        return qs

    docs = []
    for inv in _window(
        cari.invoices.filter(status="cancelled").select_related("currency"), "date"
    ):
        docs.append({
            "kind": _("Invoice"), "label": inv.display_number, "date": inv.date,
            "amount": inv.total, "currency": inv.currency,
            "url": _reverse("accounts:invoice_detail", args=[inv.pk]),
        })
    for pay in _window(
        cari.payments.filter(status="cancelled").select_related("currency"), "date"
    ):
        docs.append({
            "kind": pay.get_type_display(), "label": pay.number, "date": pay.date,
            "amount": pay.amount, "currency": pay.currency,
            "url": _reverse("accounts:payment_detail", args=[pay.pk]),
        })
    for chk in _window(
        cari.checks.filter(status="cancelled").select_related("currency"), "issue_date"
    ):
        docs.append({
            "kind": chk.get_instrument_display(), "label": chk.serial_no,
            "date": chk.issue_date, "amount": chk.amount, "currency": chk.currency,
            "url": _reverse("accounts:check_detail", args=[chk.pk]),
        })
    # date can be None on nothing here, but a stable order beats three
    # queries' worth of arbitrary interleaving.
    docs.sort(key=lambda d: (d["date"], d["label"]), reverse=True)
    return docs


@method_decorator(login_required, name="dispatch")
class CariStatement(View):
    template_name = "accounts/cari_statement.html"

    def get(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)

        # ── Filters from query string ──────────────────────────────
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or ""
        direction = (request.GET.get("direction") or "").strip()   # in / out
        status_f  = (request.GET.get("status") or "").strip()      # cancelled

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
        # is_void is the SAME rule CariAccount.recompute_balance sums by,
        # so an unfiltered statement closes on the account's balance by
        # construction rather than by argument. See CariMovementQuerySet.
        if status_f == "cancelled":
            qs = qs.void()
        else:
            qs = qs.live()

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
            prior_qs = prior_qs.live()
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
            "cancelled_documents": (
                _cancelled_documents(cari, date_from, date_to)
                if status_f == "cancelled" else []
            ),
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
@method_decorator(login_required, name="dispatch")
class CariMovementDetail(View):
    """One ledger row, in full, and the way to correct it.

    The tables print a row across a handful of columns; this is the place
    that answers what it actually is — what it converted at and came to,
    where it sits in the running balance, who entered it, and which
    document, if any, owns it.

    That last one decides what the page offers. A hand-entered row is
    edited here. A row a document posted is not: the document recomputes
    it, so an edit made in place is overwritten the next time the document
    is touched — silently, and only sometimes. Those rows get a link to
    the document instead, which is the same rule _movement_owner already
    enforces for the pencil in the tables and for a typed URL.
    """

    template_name = "accounts/movement_detail.html"

    def get(self, request, pk, mv_pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        mv = get_object_or_404(
            CariMovement.objects.select_related(
                "currency", "cari", "book", "created_by__user"
            ),
            pk=mv_pk, cari=cari,
        )

        # The balance as of this row: everything up to and including it,
        # by the same rule the account page and the statement sum by.
        # Rebuilt rather than passed in, so the figure is right whichever
        # page the user arrived from.
        running = cari.movements.live().filter(
            Q(date__lt=mv.date) | Q(date=mv.date, id__lte=mv.id)
        ).aggregate(s=Sum("amount_base"))["s"] or Decimal("0.00")

        row = _attach_links([{"mv": mv, "balance_after": running}])[0]
        return render(request, self.template_name, {
            "cari": cari,
            "mv": mv,
            "row": row,
            "balance_after": running,
        })


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
# Account transfer (virman) — the document behind a pair of ledger legs
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariTransferDetail(View):
    """One transfer, in full, and the way to correct it.

    Sits at transfers/<pk>/ with the edit form at transfers/<pk>/edit/,
    the shape every other document here already has — invoices/<pk>/ and
    invoices/<pk>/edit/, movements/<pk>/ and movements/<pk>/edit/. Landing
    here after a save is the point: the statement it used to redirect to
    answers for one of the two accounts and says nothing about what was
    just written to the other.

    Both legs are named, each linking to its own ledger row, because a
    transfer is only ever half-visible from either account's statement.
    """

    template_name = "accounts/transfer_detail.html"

    def get(self, request, pk):
        transfer = get_object_or_404(
            CariTransfer.objects.select_related(
                "from_cari", "to_cari", "currency", "book", "created_by__user",
                "from_movement", "to_movement",
            ),
            pk=pk,
        )
        return render(request, self.template_name, {
            "transfer": transfer,
            # The legs, paired with the account each one lands on, so the
            # template does not have to re-derive which is which.
            "legs": [
                ("from", transfer.from_cari, transfer.from_movement),
                ("to", transfer.to_cari, transfer.to_movement),
            ],
        })


@method_decorator(login_required, name="dispatch")
class CariTransferEdit(View):
    """Correct a posted transfer, from either of the legs it wrote.

    A transfer owns two ledger rows in two different accounts, so neither
    is editable where it sits: moving one leg alone would take a balance
    out of one account without putting it into the other. _movement_owner
    has always said so — but it had nowhere to send the user, because a
    transfer could be made and never looked at again. This is that page.

    Saving hands the whole corrected transfer to repost(), which rewrites
    both legs in place from ONE rate on ONE date — the invariant that makes
    the pair cancel, and the reason neither leg is editable on its own. The
    rows keep their ids, so a link to a leg survives a correction.

    The save and the rewrite run in one transaction, so a rejected edit
    leaves the transfer posted exactly as it was.
    """

    template_name = "accounts/transfer_form.html"

    def _transfer(self, pk):
        return get_object_or_404(
            CariTransfer.objects.select_related(
                "from_cari", "to_cari", "currency", "book", "created_by__user"
            ),
            pk=pk,
        )

    def _render(self, request, transfer, form=None):
        return render(request, self.template_name, {
            "transfer": transfer,
            "form": form or CariTransferForm(instance=transfer, book=transfer.book),
            # Where to go back to. A transfer belongs to two accounts and
            # favours neither, so the source is where the operator most
            # likely came from — the leg that lost the balance.
            "back_cari": transfer.from_cari,
            # What the rate row converts INTO. Deliberately
            # settings.BASE_CURRENCY_CODE and not the book's own base, for
            # the reason MakeInTransfer.render_page spells out: the ledger
            # converts against the former, so taking the latter would let
            # the page label and convert against one currency while the
            # rows it writes used another.
            "base_currency": CurrencyCategory.objects.filter(
                code=getattr(settings, "BASE_CURRENCY_CODE", "USD")
            ).first(),
        })

    def get(self, request, pk):
        return self._render(request, self._transfer(pk))

    def post(self, request, pk):
        transfer = self._transfer(pk)
        form = CariTransferForm(request.POST, instance=transfer, book=transfer.book)
        if not form.is_valid():
            return self._render(request, transfer, form=form)
        try:
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.book = form.cleaned_data.get("book") or transfer.book
                transfer.save()
                transfer.repost(user=request.user)
        except ValidationError as exc:
            # The model guards the same rules the form does; this is the
            # belt to the form's braces rather than a path the UI reaches.
            form.add_error(None, exc.messages)
            return self._render(request, self._transfer(pk), form=form)

        messages.success(request, _g("Transfer updated."))
        return redirect("accounts:transfer_detail", pk=transfer.pk)


@method_decorator(login_required, name="dispatch")
class CariTransferUndo(View):
    """Take a transfer back: both legs go, both balances re-derive.

    Deleted rather than reversed with counter-movements — see
    CariTransfer.unpost(). The transfer row itself goes too, so an undone
    transfer leaves no document behind claiming to have moved something.
    """

    def post(self, request, pk):
        transfer = get_object_or_404(CariTransfer, pk=pk)
        from_pk = transfer.from_cari_id
        with transaction.atomic():
            transfer.unpost()
            transfer.delete()
        messages.success(request, _g("Transfer undone."))
        return redirect("accounts:statement", pk=from_pk)


# ---------------------------------------------------------------------------
# Delete (soft — flips is_active=False; hard delete only if no movements)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CariDelete(View):
    def post(self, request, pk):
        cari = get_object_or_404(CariAccount, pk=pk)
        book_id = cari.book_id          # read before the row may go
        if cari.movements.exists():
            cari.is_active = False
            cari.save(update_fields=["is_active"])
            messages.info(request, _g("Account %(code)s was deactivated (not deleted because it has movements).") % {"code": cari.code})
        else:
            code = cari.code
            cari.delete()
            messages.success(request, _g("Account %(code)s deleted.") % {"code": code})
        return redirect("accounts:list", book_id=book_id)
