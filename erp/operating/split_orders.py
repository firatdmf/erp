"""An order split across books, seen as the one order it is.

A customer who wants goods off two books' shelves gets two orders — one per
book, each billing its own current account (see OrderCreate) — tied by
Order.split_group. That is right for the books and wrong for everybody
looking at the order: it is one request, packed and shipped together. So on
screen the halves are one combined order, named by both numbers
("ORD-2026-000011 & ORD-2026-000012"), while each half keeps its own number,
account, posting and invoice.

Seeing the combined order is the one exception to book scoping: whoever may
open one half may see the whole of it — lines, prices, totals — though never
the other book's account, invoice or payments.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from accounting.services_accounts import member_can_use_book

from .models import Order


def order_book(order):
    account = getattr(order, "current_account", None)
    return getattr(account, "book", None) if account is not None else None


def split_halves(order):
    """Every order of the request, this one included, first made first —
    the order the combined name lists them in. Just [order] when it is not
    split."""
    if not order.split_group:
        return [order]
    return list(Order.objects.filter(split_group=order.split_group)
                .select_related("current_account__book", "currency")
                .order_by("pk"))


# What the halves of a split order share: everything about the request
# itself, which is one — its date, notes, addresses, the customer's notices,
# the cargo it goes out in. A change to any of these on one half is a change
# to all of them (keep_halves_alike). What stays each half's own: its number,
# status (moved together by apply_order_status_change), account, currency
# rate, invoice and payment details — each book's business.
SHARED_FIELDS = (
    "order_date", "notes", "internal_notes", "notify_customer",
    "delivery_address_title", "delivery_address", "delivery_city",
    "delivery_country", "delivery_phone",
    "billing_address_title", "billing_address", "billing_city",
    "billing_country", "billing_phone",
    "is_guest_order", "guest_email", "guest_phone", "guest_first_name",
    "guest_last_name",
    "carrier", "tracking_number", "shipped_at", "delivered_at",
)
# Shared too, but who the customer is decides which account each half bills
# in its own book, so a change also moves every half onto that account.
CUSTOMER_FIELDS = ("contact", "company", "web_client", "charge_contact_personally",
                   "is_retail_order")


def _attnames(names):
    return {name: Order._meta.get_field(name).attname for name in names}


def shared_values_in_db(order):
    """The shared fields as `order`'s row holds them, before a save — so the
    save can tell which ones it really changes. None for an order that is
    not split, or not saved yet."""
    if not order.pk or not order.split_group:
        return None
    names = _attnames(SHARED_FIELDS + CUSTOMER_FIELDS)
    return Order.objects.filter(pk=order.pk).values(*names.values()).first()


def keep_halves_alike(order, before, fields=None):
    """After `order` is saved: give its other halves what the save changed
    in the shared fields, so the halves never read differently.

    `before` is shared_values_in_db from just before the save. Only what
    the save changed is copied — a half saved from a copy that was loaded
    before another half changed something does not undo that change on the
    rest. `fields` is the save's update_fields, when it named them.

    A changed customer moves every half onto that customer's account in
    its own book (settle_half_account); SplitCurrencyClash, raised when one
    of those accounts cannot be in the order's currency, rolls the caller's
    transaction back."""
    if not order.split_group or before is None:
        return
    from django.utils import timezone

    names = _attnames(SHARED_FIELDS + CUSTOMER_FIELDS)
    changed = [name for name, attname in names.items()
               if (fields is None or name in fields)
               and getattr(order, attname) != before.get(attname)]
    if not changed:
        return
    others = Order.objects.filter(split_group=order.split_group).exclude(pk=order.pk)
    plain = {names[n]: getattr(order, names[n]) for n in changed if n in SHARED_FIELDS}
    if plain:
        others.update(**plain, updated_at=timezone.now())
    customer = [n for n in changed if n in CUSTOMER_FIELDS]
    if not customer:
        return
    for half in others.select_related("current_account__book", "currency"):
        for name in customer:
            setattr(half, names[name], getattr(order, names[name]))
        half._keeping_alike = True
        half.save(update_fields=customer + ["updated_at"])
        settle_half_account(half)


def settle_half_account(half, member=None):
    """Bill `half` to its customer's account in the half's OWN book, in the
    order's currency, and re-post it there. A customer cleared off the
    order leaves the half where it is: its book is known only through its
    account."""
    from accounting.services_accounts import (
        align_split_account_currency, check_split_currency,
        get_or_create_current_account_for_order,
        get_or_create_retail_current_account, post_order_movement,
    )
    book = order_book(half)
    if book is None:
        return
    if half.is_retail_order:
        account = get_or_create_retail_current_account(member=member, book=book)
    else:
        account = get_or_create_current_account_for_order(half, member=member, book=book)
    if account is None:
        return
    check_split_currency(account, half.currency)
    align_split_account_currency(account, half.currency)
    if half.current_account_id != account.pk:
        half.current_account = account
        half._keeping_alike = True
        half.save(update_fields=["current_account", "updated_at"])
    post_order_movement(half, member=member)


def page_line_prefetches():
    """What an order page reads off every line, fetched in a few queries
    for all of them rather than a few per line: product and variant, the
    product's photos (first one shown), the warehouse rows and attribute
    values the line is described by."""
    from django.db.models import Prefetch
    from marketing.models import ProductFile
    return [
        "items__product", "items__product_variant",
        Prefetch("items__product__files", queryset=ProductFile.objects.order_by("pk")),
        Prefetch("items__product_variant__files", queryset=ProductFile.objects.order_by("pk")),
        "items__product_variant__warehouse_products",
        "items__product_variant__product_variant_attribute_values"
        "__product_variant_attribute",
    ]


def page_halves(order):
    """split_halves for the order's page — reading only — with every
    half's lines, their costs and adjustments loaded in one go. `order`
    itself stands in for its own half, so what the page already loaded
    for it is used rather than fetched again.

    Not for anything that changes lines: the loaded lines would go stale."""
    from marketing.models import attach_live_costs
    if not order.split_group:
        halves = [order]
    else:
        halves = [order if h.pk == order.pk else h for h in
                  Order.objects.filter(split_group=order.split_group)
                  .select_related("current_account__book", "currency")
                  .prefetch_related(*page_line_prefetches(), "adjustments")
                  .order_by("pk")]
    # Every line's cost in one query: the cost and profit figures read
    # them line by line.
    attach_live_costs(it.product_variant for h in halves for it in h.items.all()
                      if it.product_variant_id)
    return halves


def order_packs(order):
    """The packages of the whole order, numbered one run for all its halves.

    The halves go out together, so a sack can hold goods off both books'
    shelves: a split order's packages are those of every half, and the
    rolls of either half may go into any of them. A package still belongs
    to one half (Pack.order) — new ones to the first made, see
    pack_holder — but that says nothing of what is in it."""
    from .models import Pack
    if order.split_group:
        packs = Pack.objects.filter(order__split_group=order.split_group)
    else:
        packs = Pack.objects.filter(order=order)
    return packs.select_related("order").order_by("pack_number", "order_id")


def pack_holder(order):
    """The order a new package of `order` is made on: the first made half,
    whichever half the packer has open."""
    if not order.split_group:
        return order
    return Order.objects.filter(split_group=order.split_group).order_by("pk").first()


def lend_cargo_info(order, halves):
    """Give `order`, in memory only, the carrier, tracking number and
    shipping dates a sibling has and it lacks — so either half's page
    reads the same. Halves now take their cargo info together
    (apply_order_status_change); this is for the ones saved before."""
    for field in ("carrier", "tracking_number", "shipped_at", "delivered_at"):
        if not getattr(order, field):
            for half in halves:
                if half.pk != order.pk and getattr(half, field):
                    setattr(order, field, getattr(half, field))
                    break


def halves_in_step(order):
    """The halves standing where `order` stands, itself first-made-first
    among them — the ones a notice to the customer speaks for. A half
    cancelled on its own earlier is no part of an order that has shipped."""
    return [h for h in split_halves(order)
            if h.pk == order.pk or h.status == order.status]


def half_number(order):
    return order.order_number or f"#{order.pk}"


def combined_number(halves):
    """"ORD-2026-000011 & ORD-2026-000012" — both halves, first made first."""
    return " & ".join(half_number(h) for h in halves)


def split_order_guarded(view):
    """book_guarded for the order page, with the split-order exception.

    The viewer's own book → the page. Another book, but one of its halves is
    in a book the viewer holds → that half's page, which shows the whole
    combined order without opening the other book's accounts. Neither → 404,
    exactly as book_guarded (which books exist is not to be probed).
    """
    @wraps(view)
    def wrapper(request, *args, pk=None, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        order = get_object_or_404(Order.objects.select_related("current_account__book"), pk=pk)
        member = getattr(request.user, "member", None)
        book = order_book(order)
        if member_can_use_book(member, book):
            request.book = book
            return view(request, *args, pk=pk, **kwargs)
        for half in split_halves(order):
            if half.pk != order.pk and member_can_use_book(member, order_book(half)):
                return redirect("operating:order_detail", pk=half.pk)
        raise Http404("No such record.")
    return wrapper


def label_split_rows(orders):
    """Put the combined name, the other halves' books and the combined
    total on every split order in a list, in a few queries for the whole
    page. The total is the whole order's, as its page shows it — None
    for an older split in two currencies, which has no one sum."""
    groups = {o.split_group for o in orders if o.split_group}
    if not groups:
        return
    by_group = {}
    for half in (Order.objects.filter(split_group__in=groups)
                 .select_related("current_account__book", "currency")
                 .prefetch_related("items", "adjustments").order_by("pk")):
        by_group.setdefault(half.split_group, []).append(half)
    for order in orders:
        halves = by_group.get(order.split_group) if order.split_group else None
        if not halves or len(halves) < 2:
            continue
        order.combined_number = combined_number(halves)
        order.split_other_books = [
            getattr(order_book(h), "name", "") for h in halves if h.pk != order.pk]
        totals = combined_totals(halves)
        order.combined_total = totals[0][1] if len(totals) == 1 else None


def order_rows(orders):
    """A list of orders as a customer's card lists them: one row per
    order, a split order's halves folded into the first of them listed.

    Every row gets row_numbers (both halves' for a split), row_totals —
    [(symbol, grand total)], the halves standing together added up — and
    row_pks, the halves of it in `orders`: the ones the viewer may print.
    Pass the orders with items and adjustments prefetched; the halves
    not in `orders` are fetched here, in one query.
    """
    orders = list(orders)
    groups = {o.split_group for o in orders if o.split_group}
    by_group = {}
    if groups:
        for half in (Order.objects.filter(split_group__in=groups)
                     .select_related("currency")
                     .prefetch_related("items", "adjustments").order_by("pk")):
            by_group.setdefault(half.split_group, []).append(half)
    rows, first_of = [], {}
    for o in orders:
        halves = by_group.get(o.split_group, []) if o.split_group else []
        if len(halves) > 1:
            if o.split_group in first_of:
                first_of[o.split_group].row_pks.append(o.pk)
                continue
            first_of[o.split_group] = o
            o.row_numbers = [half_number(h) for h in halves]
            # Not a half cancelled on its own: it is no part of what the
            # order comes to. A half merely a stage ahead of the other is.
            standing = [h for h in halves if h.status != "cancelled"]
            o.row_totals = combined_totals(standing or halves)
        else:
            o.row_numbers = [half_number(o)]
            o.row_totals = [(o.currency_symbol, o.total_value() or 0)]
        o.row_pks = [o.pk]
        rows.append(o)
    return rows


def other_halves_for_page(order, member, admin=False, halves=None):
    """The other halves of `order`, dressed for its page: lines in the same
    order the page lists its own, with the rolls scanned for each, the
    half's totals, whether the viewer may open it, and whether its lines
    show what they cost — to an admin only; cost is otherwise its own
    book's business."""
    from decimal import Decimal
    from marketing import units
    from .views import (_order_item_variant_lines, _order_item_description,
                        _stock_taken_label, attach_line_purchases)

    others = []
    for half in (halves if halves is not None else page_halves(order)):
        if half.pk == order.pk:
            continue
        items = sorted(
            half.items.all(),
            key=lambda i: ((getattr(i.product, "title", "") or "").casefold(),
                           (getattr(i.product_variant, "variant_sku", "") or ""), i.pk))
        # Each line opens onto its rolls as this half's own lines do: the
        # ones held for it, and those its purchases say are coming.
        attach_line_purchases(items, half.supplier_purchases.exclude(status="cancelled")
                              .select_related("intake_warehouse").order_by("-date", "-pk"))
        tracked = half.classify_items_by_tracking(items)
        held = {}
        reservations = list(half.stock_reservations.select_related(
            "stock_item", "warehouse_product__warehouse", "pack",
            "warehouse_product__catalog_variant__product").order_by("-created_at"))
        for r in reservations:
            if r.order_item_id:
                held.setdefault(r.order_item_id, []).append(r)
        # Every roll held for the half, on a line or not: what it adds to
        # the page's "Total scanned".
        half.scanned_count = len(reservations)
        half.scanned_meters = sum((r.quantity or Decimal("0") for r in reservations), Decimal("0"))
        half.taken_reservations = reservations
        for it in items:
            rs = held.get(it.pk, [])
            it.scanned_count = len(rs)
            it.scanned_meters = sum((r.quantity or Decimal("0") for r in rs), Decimal("0"))
            it.scanned_label = _stock_taken_label(rs)
            it.item_reservations = rs
            it.is_tracked = bool(tracked.get(it.pk, False))
            it.sold_by_count = units.by_variant(getattr(it.product, "tracking", None))
            it.variant_lines = _order_item_variant_lines(it)
            it.description_lines, it.description_worded = _order_item_description(it)
        half.page_items = items
        half.book_name = getattr(order_book(half), "name", "")
        half.may_open = member_can_use_book(member, order_book(half))
        half.show_cost = admin
        others.append(half)
    return others


def combined_totals(halves):
    """The combined order's grand total, one entry per currency — one entry,
    now that a split is kept in one currency; more only for an older split."""
    totals = {}
    for half in halves:
        key = half.currency_symbol
        totals[key] = totals.get(key, 0) + (half.total_value() or 0)
    return list(totals.items())


def profit_figures(order, member, admin=False, halves=None):
    """What the order's page says the order cost and made: cost, profit,
    revenue and margin, and under "others" what the other halves put in.

    A split order counts every half — it is one sale — but only for an
    admin or a viewer who may open every half, and only while the halves
    share a currency. Otherwise the figures are the one order's, as for any order:
    another book's cost is not shown to someone kept out of that book, and
    two currencies have no one sum.
    """
    from decimal import Decimal

    def figures(orders):
        return {
            "cost": sum((o.total_cost() for o in orders), Decimal("0")),
            "profit": sum((o.gross_profit() for o in orders), Decimal("0")),
            "revenue": sum((Decimal(str(o.total_value() or 0)) for o in orders), Decimal("0")),
        }

    others = []
    if halves is None:
        halves = page_halves(order)
    if (len(halves) > 1 and len({h.currency_symbol for h in halves}) == 1
            and (admin or all(member_can_use_book(member, order_book(h)) for h in halves))):
        others = [h for h in halves if h.pk != order.pk]
    out = figures([order] + others)
    out["others"] = figures(others) if others else None
    out["margin"] = ((out["profit"] / out["revenue"] * Decimal("100")).quantize(Decimal("0.1"))
                     if out["revenue"] > 0 else None)
    return out
