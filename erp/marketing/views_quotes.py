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

from .models import Quote, QuoteItem, QuoteItemRoll


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


def _resolve_rolls(raw_rolls, product, variant, already_quoted, taken):
    """The rolls picked for one line, checked: each is a roll of this
    line's product, on any book's shelves, quoted for no more than it
    holds. A roll picked just now must also be free of order holds; one
    the quote already had is kept even if an order has taken it since —
    the quote pages flag it, and conversion refuses it, but a save of
    some other change must not fail over it. Returns [(roll, quantity)]."""
    from operating.models import OrderStockReservation, WarehouseProductItem
    from django.db.models import Sum
    out = []
    for raw in raw_rolls or []:
        rid = str(raw.get("id") or "").strip()
        if not rid.isdigit():
            continue
        roll = (WarehouseProductItem.objects.select_related("product__warehouse")
                .filter(pk=int(rid)).first())
        if roll is None:
            raise QuoteSaveError(_("A picked roll no longer exists — pick the line's rolls again."))
        code = roll.barcode or f"#{roll.pk}"
        wp = roll.product
        if variant is not None:
            matches = wp.catalog_variant_id == variant.pk
        else:
            matches = bool(product and product.sku and (wp.sku or "").lower() == product.sku.lower())
        if not matches:
            raise QuoteSaveError(_("Roll %(roll)s is not a roll of this line's product.") % {"roll": code})
        if not wp.warehouse.accounting_book_id:
            raise QuoteSaveError(_("Roll %(roll)s stands in a warehouse no book owns.") % {"roll": code})
        if roll.pk in taken:
            raise QuoteSaveError(_("Roll %(roll)s is on two lines.") % {"roll": code})
        taken.add(roll.pk)
        qty = _dec(raw.get("quantity"))
        phys = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
        if roll.pk not in already_quoted:
            held = (OrderStockReservation.objects.filter(stock_item=roll, consumed=False)
                    .aggregate(s=Sum("quantity"))["s"]) or Decimal("0")
            phys = (phys or Decimal("0")) - held
        if roll.status == "consumed" and roll.pk not in already_quoted:
            phys = Decimal("0")
        if qty <= 0:
            qty = phys or Decimal("0")
        if qty <= 0 or (roll.pk not in already_quoted and qty > phys):
            raise QuoteSaveError(_("Roll %(roll)s has only %(free)s free.")
                                 % {"roll": code, "free": max(phys or 0, 0)})
        out.append((roll, qty))
    return out


def _resolve_lines(data, already_quoted=frozenset()):
    lines = []
    taken = set()
    for raw in data.get("items") or []:
        qty = _dec(raw.get("quantity"))
        if qty <= 0 and not raw.get("rolls"):
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
        rolls = []
        if raw.get("rolls") and product is not None:
            rolls = _resolve_rolls(raw.get("rolls"), product, variant, already_quoted, taken)
            # The line is the rolls: its quantity is what they add up to,
            # never a figure typed beside them.
            qty = sum((q for _r, q in rolls), Decimal("0"))
        if qty <= 0:
            continue
        lines.append({"product": product, "variant": variant, "description": description,
                      "quantity": qty, "unit": unit, "price": _dec(raw.get("price")),
                      "rolls": rolls})
    if not lines:
        raise QuoteSaveError(_("Add at least one line with a quantity."))
    return lines


def _prefill_customer(request):
    """An unsaved quote naming the customer a new quote was started for,
    or None. The CRM contact and company pages open the form with
    ?contact=<id> or ?company=<id>, so the quote starts out theirs."""
    for kind, model in (("company", Company), ("contact", Contact)):
        pk = (request.GET.get(kind) or "").strip()
        if pk.isdigit():
            found = model.objects.filter(pk=int(pk)).first()
            if found is not None:
                return Quote(**{kind: found})
    return None


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
            by_line = {}
            for link in quote.roll_links():
                by_line.setdefault(link.quote_item_id, []).append({
                    "id": link.stock_item_id, "barcode": link.barcode,
                    "quantity": str(link.quantity), "available": float(link.available),
                    "state": link.state, "held_by": list(link.held_by),
                    "book": link.book.name if link.book else "",
                    "book_id": link.book.pk if link.book else None,
                })
            for it in quote.items.select_related("product", "product_variant__product"):
                items.append({
                    "sku": it.sku(), "label": it.label() if it.product_id else "",
                    "description": it.description, "quantity": str(it.quantity),
                    "unit": it.unit, "price": str(it.price),
                    "rolls": [r for r in by_line.get(it.pk, []) if r["id"]],
                })
        current_book = getattr(request, "book", None)
        currencies = list(CurrencyCategory.objects.order_by("code"))
        base = _base_currency()
        return render(request, self.template_name, {
            # The sign each amount on the form is written with. A currency
            # with no symbol of its own is written with its code.
            "currency_signs": {c.code: c.symbol or c.code for c in currencies},
            "base_currency_code": base.code if base else "",
            "quote": quote,
            "prefill": None if quote else _prefill_customer(request),
            "items_json": json.dumps(items),
            "currencies": currencies,
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
                quote.internal_notes = (data.get("internal_notes") or "")[:4000]
                code = (data.get("currency") or "").strip().upper()
                quote.currency = (CurrencyCategory.objects.filter(code=code).first() if code
                                  else None) or _customer_currency(quote) or _base_currency()
                already_quoted = (set(QuoteItemRoll.objects.filter(quote_item__quote=quote)
                                      .values_list("stock_item_id", flat=True))
                                  if quote.pk else set())
                lines = _resolve_lines(data, already_quoted)
                quote.save()
                quote.items.all().delete()
                for n, line in enumerate(lines, start=1):
                    item = QuoteItem.objects.create(
                        quote=quote, line_no=n, product=line["product"],
                        product_variant=line["variant"], description=line["description"],
                        quantity=line["quantity"], unit=line["unit"], price=line["price"])
                    QuoteItemRoll.objects.bulk_create(
                        QuoteItemRoll(quote_item=item, stock_item=roll, barcode=roll.barcode or "",
                                      quantity=qty)
                        for roll, qty in line["rolls"])
        except QuoteSaveError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        return JsonResponse({"success": True, "quote_id": quote.pk,
                             "url": reverse("marketing:quote_detail", args=[quote.pk])})


# ── Detail / print ───────────────────────────────────────────────────

def _lines_by_book(quote, items):
    """The quote's lines under the books their rolls stand in — the same
    cut acceptance makes (_quote_parts_by_book), so the page shows the
    orders the quote would become. A line with rolls on two books' shelves
    shows under each, with that book's rolls and metres; a line with no
    rolls sits under the quote's own book. The quote's book comes first.
    Every roll is listed whichever book the viewer works in: a quote
    offers the house's stock, and the barcodes are what it offers."""
    from types import SimpleNamespace
    from marketing import units
    from operating.views import _order_item_variant_lines

    groups = {}

    def group(book):
        key = book.pk if book else None
        if key not in groups:
            groups[key] = SimpleNamespace(book=book, parts=[], subtotal=Decimal("0"),
                                          rolls=0, is_own=(key == quote.book_id))
        return groups[key]

    for it in items:
        files = list(it.product.files.all()) if it.product_id else []
        image = next((f.file_url for f in files if getattr(f, "file_url", None)), "")
        variant_lines = _order_item_variant_lines(it) if it.product_variant_id else []
        pack = getattr(it.product, "pack_type", None) or units.DEFAULT_PACK
        by_book = {}
        for link in it.linked_rolls:
            book = link.book or quote.book
            by_book.setdefault(book.pk, (book, []))[1].append(link)
        pieces = list(by_book.values()) or [(quote.book, [])]
        for book, rolls in pieces:
            qty = sum((link.quantity for link in rolls), Decimal("0")) if rolls else it.quantity
            g = group(book)
            part = SimpleNamespace(
                item=it, key=f"{it.pk}-{book.pk if book else 0}", rolls=rolls, quantity=qty,
                amount=qty * (it.price or Decimal("0")), image=image, variant_lines=variant_lines,
                stale_count=sum(1 for link in rolls if link.state != "free"),
                pack_label=(f"{len(rolls)} {units.pack_noun(pack, len(rolls))}" if rolls else ""))
            g.parts.append(part)
            g.subtotal += part.amount
            g.rolls += len(rolls)
    own = groups.pop(quote.book_id, None)
    rest = sorted(groups.values(), key=lambda g: ((g.book.name if g.book else "") or "", g.book.pk if g.book else 0))
    return ([own] if own and own.parts else []) + rest


def _print_sections(book_groups):
    """The printed quote's lines, book by book as _lines_by_book cuts them,
    and within each book by the warehouse whose shelf the rolls stand on —
    what each order will be and where its goods are picked from. A line
    with rolls in two warehouses prints under each, with that warehouse's
    rolls and metres; a line with no rolls closes its book, under no
    warehouse."""
    from types import SimpleNamespace
    from marketing import units

    sections = []
    for g in book_groups:
        shelves = {}
        for part in g.parts:
            it = part.item
            pack = getattr(it.product, "pack_type", None) or units.DEFAULT_PACK
            by_wh = {}
            for link in part.rolls:
                wh = link.stock_item.product.warehouse if link.stock_item_id else None
                by_wh.setdefault(wh.pk if wh else None, (wh, []))[1].append(link)
            for wh, rolls in (list(by_wh.values()) or [(None, [])]):
                qty = sum((link.quantity for link in rolls), Decimal("0")) if rolls else part.quantity
                shelf = shelves.setdefault(wh.pk if wh else None,
                                           SimpleNamespace(warehouse=wh, rows=[], rolls=0))
                shelf.rows.append(SimpleNamespace(
                    item=it, rolls=rolls, quantity=qty, amount=qty * (it.price or Decimal("0")),
                    pack_label=(f"{len(rolls)} {units.pack_noun(pack, len(rolls))}" if rolls else "")))
                shelf.rolls += len(rolls)
        ordered = sorted((s for k, s in shelves.items() if k is not None),
                         key=lambda s: (s.warehouse.name or "", s.warehouse.pk))
        if None in shelves:
            ordered.append(shelves[None])
        sections.append(SimpleNamespace(book=g.book, shelves=ordered, rolls=g.rolls))
    return sections


def _quote_page_context(request, pk):
    from accounting.services_accounts import brand_name_for
    quote = get_object_or_404(
        _quotes_for(request).select_related("contact", "company", "currency", "book", "order"),
        pk=pk)
    from marketing import units
    items = list(quote.items.select_related("product", "product_variant__product")
                 .prefetch_related("product__files", "product_variant__warehouse_products"))
    links = quote.roll_links()
    by_line = {}
    for link in links:
        by_line.setdefault(link.quote_item_id, []).append(link)
    # Quantities add up per unit (metres with metres). Rolls are counted
    # by what the product comes packed as — "rolls" for cloth, "boxes"
    # for boxed goods — and only where a line names its rolls: a line
    # without them says nothing about how many there are.
    unit_totals, packs = {}, {}
    for it in items:
        it.linked_rolls = by_line.get(it.pk, [])
        it.stale_count = sum(1 for link in it.linked_rolls if link.state != "free")
        unit = (it.unit or "").strip()
        unit_totals[unit] = unit_totals.get(unit, Decimal("0")) + (it.quantity or Decimal("0"))
        if it.linked_rolls:
            pack = getattr(it.product, "pack_type", None) or units.DEFAULT_PACK
            packs[pack] = packs.get(pack, 0) + len(it.linked_rolls)
            it.pack_label = f"{len(it.linked_rolls)} {units.pack_noun(pack, len(it.linked_rolls))}"
    return {
        "quote": quote,
        "items": items,
        "book_groups": _lines_by_book(quote, items),
        "total": sum((it.line_total() for it in items), Decimal("0")),
        "unit_totals": list(unit_totals.items()),
        "pack_totals": [f"{n} {units.pack_noun(pack, n)}" for pack, n in packs.items()],
        "stale_rolls": [link for link in links if link.state != "free"],
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
    from erp.nejum_credit import brand_color, credit_html
    context = _quote_page_context(request, pk)
    context["sections"] = _print_sections(context["book_groups"])
    # Signed like the order sheet: the house's name in the house's colour,
    # and the Nejum credit for the quote's own book, which may trade
    # under a name of its own.
    context["brand_color"] = brand_color()
    context["nejum_credit_html"] = credit_html(context["quote"].book)
    from erp.pdf_render import document_response
    return document_response(request, "marketing/quote_print.html", context,
                             f"quote_{context['quote'].number}.pdf")


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


def _quote_parts_by_book(quote):
    """The quote's lines cut into the books their rolls stand in.

    Returns [(book, [(quote item, quantity, [links])...])...], the quote's
    own book first. A line whose rolls stand in two books becomes two
    lines, each the metres on that book's shelves, at the quoted price —
    the same cut the order form makes (operating.views._line_parts_by_book).
    A line with no rolls has no shelf to read and stays in the quote's
    book."""
    links = {}
    for link in (QuoteItemRoll.objects.filter(quote_item__quote=quote)
                 .select_related("stock_item__product__warehouse__accounting_book")):
        links.setdefault(link.quote_item_id, []).append(link)
    groups = {quote.book_id: (quote.book, [])}
    for it in quote.items.select_related("product", "product_variant"):
        mine = links.get(it.pk, [])
        if not mine:
            groups[quote.book_id][1].append((it, it.quantity, []))
            continue
        by_book = {}
        for link in mine:
            book = (link.stock_item.product.warehouse.accounting_book
                    if link.stock_item_id else quote.book)
            by_book.setdefault(book.pk, (book, []))[1].append(link)
        for book, book_links in by_book.values():
            qty = sum((link.quantity for link in book_links), Decimal("0"))
            groups.setdefault(book.pk, (book, []))[1].append((it, qty, book_links))
    lead = groups.pop(quote.book_id)
    rest = sorted(groups.values(), key=lambda pair: (pair[0].name or "", pair[0].pk))
    return [lead] + rest if lead[1] or not rest else rest


def _check_split_currency(quote, groups):
    """Refuse, before anything is written, a split whose other book holds
    the customer's account in a currency it can no longer leave: every
    half is priced in the quote's currency."""
    from accounting.services_accounts import (
        SplitCurrencyClash, check_split_currency, existing_customer_account,
    )
    if len(groups) < 2:
        return
    for book, _parts in groups:
        account = existing_customer_account(book=book, company=quote.company,
                                            contact=quote.contact)
        try:
            check_split_currency(account, quote.currency)
        except SplitCurrencyClash as exc:
            raise QuoteSaveError(str(exc))


def _orders_from_quote(request, quote):
    """One order per book the quote's rolls stand in, with its lines and a
    hold on every quoted roll — inside the caller's transaction, so a roll
    an order took in the last moment undoes the lot rather than leaving an
    order short of what was quoted. Returns [(order, book)], the quote's
    own book's order first; two or more are tied by one split_group, as
    the order form ties a basket drawn from two books' shelves."""
    from uuid import uuid4
    from operating.views import _create_roll_reservation

    groups = _quote_parts_by_book(quote)
    _check_split_currency(quote, groups)
    split_group = uuid4() if len(groups) > 1 else None
    created = []
    for book, parts in groups:
        order = Order(notes=quote.notes, internal_notes=quote.internal_notes,
                      contact=quote.contact, company=quote.company,
                      order_date=date.today(), created_by=request.user,
                      split_group=split_group)
        # Priced as quoted, whatever the account's default says — the
        # customer agreed to these numbers in this currency.
        order.currency = quote.currency
        order.save()
        for it, qty, links in parts:
            line = OrderItem.objects.create(
                order=order, product=it.product, product_variant=it.product_variant,
                description=it.description, quantity=qty, price=it.price)
            for link in links:
                held, capped, err = (None, False, "gone") if link.stock_item is None else \
                    _create_roll_reservation(order, line, link.stock_item, link.quantity, request.user)
                if err or capped:
                    raise QuoteSaveError(_("Roll %(roll)s is no longer free — edit the quote to drop "
                                           "or replace it.") % {"roll": link.barcode or "?"})
        OrderChange.objects.create(
            order=order, action="field", field="quote",
            new_value=_("Created from quote %(number)s") % {"number": quote.number},
            created_by=request.user)
        created.append((order, book))
    quote.status = "accepted"
    quote.order = created[0][0]
    quote.save(update_fields=["status", "order", "updated_at"])
    return created


@login_required
@require_POST
def quote_convert(request, pk):
    """The customer said yes: make the order, exactly as the order form
    would, and point the quote at it. Rolls quoted off another book's
    shelves go to that book's own order, split from this one."""
    from accounting.services_accounts import (
        align_split_account_currency, get_or_create_current_account_for_order,
        post_order_movement, stamp_order_currency,
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
    try:
        with transaction.atomic():
            created = _orders_from_quote(request, quote)
    except QuoteSaveError as exc:
        messages.error(request, str(exc))
        return redirect("marketing:quote_detail", pk=quote.pk)

    # The same finishing an order gets from the create form — outside the
    # transaction, as there: a ledger hiccup warns rather than undoing an
    # order the customer has been promised.
    split = len(created) > 1
    for order, book in created:
        try:
            order.original_snapshot = order.build_snapshot()
            order.save(update_fields=["original_snapshot"])
        except Exception:
            pass
        try:
            account = get_or_create_current_account_for_order(order, member=member, book=book)
            if account is not None and order.current_account_id != account.pk:
                order.current_account = account
                order.save(update_fields=["current_account"])
            if split:
                # One currency across the halves: each book's account is
                # put in the quote's (checked possible before any order
                # was made).
                align_split_account_currency(account, quote.currency)
            stamp_order_currency(order, account)
            post_order_movement(order, member=member)
        except Exception as exc:
            messages.warning(request, _("Order saved but its account could not be linked: %(error)s")
                             % {"error": exc})
        try:
            generate_machine_qr_for_order(order)
        except Exception:
            pass
    if split:
        messages.success(request, _("Quote %(quote)s became %(count)s orders, one per book its "
                                    "rolls stand in: %(orders)s.")
                         % {"quote": quote.number, "count": len(created),
                            "orders": ", ".join(f"{o.order_number} ({b.name})" for o, b in created)})
    else:
        messages.success(request, _("Quote %(quote)s became order %(order)s.")
                         % {"quote": quote.number, "order": created[0][0].order_number})
    return redirect("operating:order_detail", pk=created[0][0].pk)


# ── Product search for the form ──────────────────────────────────────

@login_required
def quote_roll_list(request):
    """The free rolls of `?sku=` on every book's shelves, each labelled
    with its book. Wider than the order form's list on purpose: a quote
    holds nothing, and the customer is offered whatever the house has —
    a sales rep included. Which book's order each roll ends up in is
    settled when the quote is accepted (_order_from_quote)."""
    from operating.views import free_rolls_response
    return free_rolls_response(request, Book.objects.all())


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
