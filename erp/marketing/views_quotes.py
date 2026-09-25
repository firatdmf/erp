"""Quotes — a price given to a customer before there is an order.

The order form commits stock and the ledger the moment it is saved. A
quote commits nothing: it is written, printed or sent, and either
declined or turned into an order in one step once the customer agrees
(quote_convert). The order it makes is an ordinary one — same account,
same currency stamping, same ledger posting as OrderCreate — and the
quote keeps pointing at it.
"""
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.http import require_POST

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from accounting.services_accounts import member_books
from crm.models import Company, Contact
from marketing.models import Product, ProductVariant

from operating.models import Order, OrderChange, OrderItem

from .models import Quote, QuoteItem


def _dec(value, default="0"):
    try:
        return Decimal(str(value if value not in (None, "") else default).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _books_for(request):
    return member_books(getattr(request.user, "member", None))


def _quotes_for(request):
    """Quotes the member may see: those in their books, plus any filed
    under no book at all."""
    return Quote.objects.filter(Q(book__in=_books_for(request)) | Q(book__isnull=True))


def _customer_currency(quote):
    """The currency the customer's account in the quote's book is kept
    in, if they have one — the default a quote prices in."""
    if quote.book_id is None:
        return None
    account = None
    if quote.company_id:
        account = CurrentAccount.objects.filter(book=quote.book, company_id=quote.company_id).first()
    elif quote.contact_id:
        contact = quote.contact
        if contact.company_id:
            account = CurrentAccount.objects.filter(book=quote.book, company_id=contact.company_id).first()
        account = account or CurrentAccount.objects.filter(book=quote.book, contact_id=contact.pk).first()
    return getattr(account, "default_currency", None)


def _base_currency():
    from django.conf import settings as _s
    return CurrencyCategory.objects.filter(code=getattr(_s, "BASE_CURRENCY_CODE", "USD")).first()


# ── List ─────────────────────────────────────────────────────────────

@login_required
def quote_list(request):
    qs = (_quotes_for(request)
          .select_related("contact", "company", "currency", "book", "order")
          .prefetch_related("items"))
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    if status == "expired":
        qs = qs.filter(status__in=["draft", "sent"], valid_until__lt=date.today())
    elif status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(customer_name__icontains=q)
                       | Q(contact__name__icontains=q) | Q(company__name__icontains=q))
    return render(request, "marketing/quote_list.html", {
        "quotes": qs[:200],
        "status": status,
        "q": q,
        "status_choices": Quote.STATUS_CHOICES + [("expired", _("Expired"))],
    })


# ── Form (new / edit) ────────────────────────────────────────────────

class QuoteSaveError(Exception):
    pass


def _resolve_customer(quote, data):
    raw = data.get("customer") or {}
    kind = (raw.get("type") or "").strip()
    pk = str(raw.get("pk") or "").strip()
    quote.contact = quote.company = None
    if kind == "contact" and pk.isdigit():
        quote.contact = Contact.objects.filter(pk=int(pk)).first()
        if quote.contact is None:
            raise QuoteSaveError(_("The customer picked was not found."))
    elif kind == "company" and pk.isdigit():
        quote.company = Company.objects.filter(pk=int(pk)).first()
        if quote.company is None:
            raise QuoteSaveError(_("The customer picked was not found."))
    quote.customer_name = (data.get("customer_name") or "")[:200].strip()
    quote.customer_email = (data.get("customer_email") or "")[:254].strip()
    quote.customer_phone = (data.get("customer_phone") or "")[:40].strip()
    if not (quote.contact_id or quote.company_id or quote.customer_name):
        raise QuoteSaveError(_("Say who the quote is for — a CRM customer or a name."))


def _resolve_lines(data):
    lines = []
    for raw in data.get("items") or []:
        qty = _dec(raw.get("quantity"))
        if qty <= 0:
            continue
        sku = (raw.get("sku") or "").strip()
        product = variant = None
        if sku:
            variant = ProductVariant.objects.filter(variant_sku=sku).select_related("product").first()
            if variant is not None:
                product = variant.product
            else:
                product = Product.objects.filter(sku=sku).first()
            if product is None:
                raise QuoteSaveError(_("No catalog product has the SKU %(sku)s.") % {"sku": sku})
        description = (raw.get("description") or "")[:300].strip()
        if product is None and not description:
            raise QuoteSaveError(_("A line needs a product or a description."))
        unit = (raw.get("unit") or "")[:20].strip()
        if not unit and product is not None:
            unit = getattr(product, "unit", "") or ""
        lines.append({"product": product, "variant": variant, "description": description,
                      "quantity": qty, "unit": unit, "price": _dec(raw.get("price"))})
    if not lines:
        raise QuoteSaveError(_("Add at least one line with a quantity."))
    return lines


@method_decorator(login_required, name="dispatch")
class QuoteForm(View):
    template_name = "marketing/quote_form.html"

    def _get_quote(self, request, pk):
        if pk is None:
            return None
        quote = get_object_or_404(_quotes_for(request), pk=pk)
        if not quote.can_edit:
            messages.error(request, _("A quote that was accepted or declined can't be edited."))
            return None if request.method == "GET" else quote
        return quote

    def get(self, request, pk=None):
        quote = self._get_quote(request, pk) if pk else None
        if pk and quote is None:
            return redirect("marketing:quote_detail", pk=pk)
        items = []
        if quote:
            for it in quote.items.select_related("product", "product_variant__product"):
                items.append({
                    "sku": it.sku(), "label": it.label() if it.product_id else "",
                    "description": it.description, "quantity": str(it.quantity),
                    "unit": it.unit, "price": str(it.price),
                })
        current_book = getattr(request, "book", None)
        return render(request, self.template_name, {
            "quote": quote,
            "items_json": json.dumps(items),
            "currencies": CurrencyCategory.objects.order_by("code"),
            "my_books": _books_for(request),
            "default_book_id": (quote.book_id if quote else
                                (current_book.pk if current_book else None)),
            "today": date.today().isoformat(),
        })

    def post(self, request, pk=None):
        try:
            data = json.loads((request.body or b"").decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"success": False, "error": _("Invalid data.")}, status=400)
        quote = None
        if pk is not None:
            quote = get_object_or_404(_quotes_for(request), pk=pk)
            if not quote.can_edit:
                return JsonResponse({"success": False, "error": _(
                    "A quote that was accepted or declined can't be edited.")}, status=400)
        try:
            with transaction.atomic():
                if quote is None:
                    quote = Quote(created_by=request.user)
                book_id = str(data.get("book_id") or "").strip()
                quote.book = (_books_for(request).filter(pk=int(book_id)).first()
                              if book_id.isdigit() else None)
                if quote.book is None:
                    raise QuoteSaveError(_("Pick the book this quote belongs to."))
                _resolve_customer(quote, data)
                quote.date = _parse_date(data.get("date")) or date.today()
                quote.valid_until = _parse_date(data.get("valid_until"))
                quote.notes = (data.get("notes") or "")[:4000]
                code = (data.get("currency") or "").strip().upper()
                quote.currency = (CurrencyCategory.objects.filter(code=code).first() if code
                                  else None) or _customer_currency(quote) or _base_currency()
                lines = _resolve_lines(data)
                quote.save()
                quote.items.all().delete()
                for n, line in enumerate(lines, start=1):
                    QuoteItem.objects.create(
                        quote=quote, line_no=n, product=line["product"],
                        product_variant=line["variant"], description=line["description"],
                        quantity=line["quantity"], unit=line["unit"], price=line["price"])
        except QuoteSaveError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        return JsonResponse({"success": True, "quote_id": quote.pk,
                             "url": reverse("marketing:quote_detail", args=[quote.pk])})


# ── Detail / print ───────────────────────────────────────────────────

def _quote_page_context(request, pk):
    from accounting.services_accounts import brand_name_for
    quote = get_object_or_404(
        _quotes_for(request).select_related("contact", "company", "currency", "book", "order"),
        pk=pk)
    items = list(quote.items.select_related("product", "product_variant__product"))
    return {
        "quote": quote,
        "items": items,
        "total": sum((it.line_total() for it in items), Decimal("0")),
        "symbol": (quote.currency.symbol if quote.currency and quote.currency.symbol else
                   (quote.currency.code + " " if quote.currency else "$")),
        "brand_line": brand_name_for(quote.book),
        "blockers": quote.conversion_blockers(),
    }


@login_required
def quote_detail(request, pk):
    return render(request, "marketing/quote_detail.html", _quote_page_context(request, pk))


@login_required
def quote_print(request, pk):
    return render(request, "marketing/quote_print.html", _quote_page_context(request, pk))


# ── Status / conversion ──────────────────────────────────────────────

@login_required
@require_POST
def quote_status(request, pk):
    """Mark a quote sent, declined, or back to draft. Accepting is
    quote_convert — it means an order."""
    quote = get_object_or_404(_quotes_for(request), pk=pk)
    new = (request.POST.get("status") or "").strip()
    if new not in ("draft", "sent", "declined"):
        messages.error(request, _("Unknown status."))
    elif quote.status == "accepted":
        messages.error(request, _("This quote became order %(number)s and stays accepted.")
                       % {"number": quote.order.order_number if quote.order_id else "—"})
    else:
        quote.status = new
        quote.save(update_fields=["status", "updated_at"])
        messages.success(request, _("Quote %(number)s marked %(status)s.")
                         % {"number": quote.number, "status": quote.get_status_display().lower()})
    return redirect("marketing:quote_detail", pk=quote.pk)


@login_required
@require_POST
def quote_convert(request, pk):
    """The customer said yes: make the order, exactly as the order form
    would, and point the quote at it."""
    from accounting.services_accounts import (
        get_or_create_current_account_for_order, post_order_movement,
        stamp_order_currency,
    )
    from operating.views import generate_machine_qr_for_order

    quote = get_object_or_404(
        _quotes_for(request).select_related("contact", "company", "currency", "book"), pk=pk)
    blockers = quote.conversion_blockers()
    if blockers:
        for why in blockers:
            messages.error(request, why)
        return redirect("marketing:quote_detail", pk=quote.pk)

    member = getattr(request.user, "member", None)
    with transaction.atomic():
        order = Order(notes=quote.notes, contact=quote.contact, company=quote.company,
                      order_date=date.today(), created_by=request.user)
        # Priced as quoted, whatever the account's default says — the
        # customer agreed to these numbers in this currency.
        order.currency = quote.currency
        order.save()
        for it in quote.items.select_related("product", "product_variant"):
            OrderItem.objects.create(
                order=order, product=it.product, product_variant=it.product_variant,
                description=it.description, quantity=it.quantity, price=it.price)
        quote.status = "accepted"
        quote.order = order
        quote.save(update_fields=["status", "order", "updated_at"])
        OrderChange.objects.create(
            order=order, action="field", field="quote",
            new_value=_("Created from quote %(number)s") % {"number": quote.number},
            created_by=request.user)

    # The same finishing an order gets from the create form — outside the
    # transaction, as there: a ledger hiccup warns rather than undoing an
    # order the customer has been promised.
    try:
        order.original_snapshot = order.build_snapshot()
        order.save(update_fields=["original_snapshot"])
    except Exception:
        pass
    try:
        account = get_or_create_current_account_for_order(order, member=member, book=quote.book)
        if account is not None and order.current_account_id != account.pk:
            order.current_account = account
            order.save(update_fields=["current_account"])
        stamp_order_currency(order, account)
        post_order_movement(order, member=member)
    except Exception as exc:
        messages.warning(request, _("Order saved but its account could not be linked: %(error)s")
                         % {"error": exc})
    try:
        generate_machine_qr_for_order(order)
    except Exception:
        pass
    messages.success(request, _("Quote %(quote)s became order %(order)s.")
                     % {"quote": quote.number, "order": order.order_number})
    return redirect("operating:order_detail", pk=order.pk)


# ── Product search for the form ──────────────────────────────────────

@login_required
def quote_product_search(request):
    """Catalog products and variants matching `q`, as JSON rows the quote
    form can put on a line. The catalog, not the shelves: a quote may
    price what is not in stock yet."""
    from operating.views_warehouse import _tr_ci_variants
    from functools import reduce
    import operator

    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    variants_q = _tr_ci_variants(q.lower())

    def fq(field):
        return reduce(operator.or_, (Q(**{f"{field}__icontains": v}) for v in variants_q))

    rows = []
    for v in (ProductVariant.objects
              .filter(fq("variant_sku") | fq("product__title") | fq("product__sku"))
              .select_related("product")
              .prefetch_related("product_variant_attribute_values__product_variant_attribute")
              .order_by("product__title", "variant_sku")[:15]):
        attrs = " ".join(a.product_variant_attribute_value
                         for a in v.product_variant_attribute_values.all()
                         if a.product_variant_attribute_value)
        rows.append({
            "sku": v.variant_sku, "variant": True,
            "label": f"{v.product.title} {attrs}".strip(),
            "unit": getattr(v.product, "unit", "") or "",
            "price": str(getattr(v.product, "price", "") or ""),
        })
    seen = {r["sku"] for r in rows}
    for p in (Product.objects.filter(fq("title") | fq("sku"))
              .order_by("title")[:15]):
        if p.sku in seen or p.variants.exists():
            continue
        rows.append({"sku": p.sku or "", "variant": False, "label": p.title,
                     "unit": getattr(p, "unit", "") or "",
                     "price": str(getattr(p, "price", "") or "")})
    return JsonResponse({"results": rows[:20]})
