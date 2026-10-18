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
            if h.pk == order.pk or h.order_status == order.order_status]


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
            # order comes to.
            o.row_totals = combined_totals(
                [h for h in halves if h.order_status == o.order_status or h.pk == o.pk])
        else:
            o.row_numbers = [half_number(o)]
            o.row_totals = [(o.currency_symbol, o.total_value() or 0)]
        o.row_pks = [o.pk]
        rows.append(o)
    return rows


def other_halves_for_page(order, member, admin=False):
    """The other halves of `order`, dressed for its page: lines in the same
    order the page lists its own, with the rolls scanned for each, the
    half's totals, whether the viewer may open it, and whether its lines
    show what they cost — to an admin only; cost is otherwise its own
    book's business."""
    from decimal import Decimal
    from .views import _order_item_variant_lines, _stock_taken_label

    halves = []
    for half in split_halves(order):
        if half.pk == order.pk:
            continue
        items = sorted(
            half.items.select_related("product", "product_variant"),
            key=lambda i: ((getattr(i.product, "title", "") or "").casefold(),
                           (getattr(i.product_variant, "variant_sku", "") or ""), i.pk))
        held = {}
        reservations = list(half.stock_reservations.select_related(
            "warehouse_product__catalog_variant__product"))
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
            it.variant_lines = _order_item_variant_lines(it)
        half.page_items = items
        half.book_name = getattr(order_book(half), "name", "")
        half.may_open = member_can_use_book(member, order_book(half))
        half.show_cost = admin
        halves.append(half)
    return halves


def combined_totals(halves):
    """The combined order's grand total, one entry per currency — one entry,
    now that a split is kept in one currency; more only for an older split."""
    totals = {}
    for half in halves:
        key = half.currency_symbol
        totals[key] = totals.get(key, 0) + (half.total_value() or 0)
    return list(totals.items())


def profit_figures(order, member, admin=False):
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
    halves = split_halves(order)
    if (len(halves) > 1 and len({h.currency_symbol for h in halves}) == 1
            and (admin or all(member_can_use_book(member, order_book(h)) for h in halves))):
        others = [h for h in halves if h.pk != order.pk]
    out = figures([order] + others)
    out["others"] = figures(others) if others else None
    out["margin"] = ((out["profit"] / out["revenue"] * Decimal("100")).quantize(Decimal("0.1"))
                     if out["revenue"] > 0 else None)
    return out
