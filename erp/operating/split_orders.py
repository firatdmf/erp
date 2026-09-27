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
    """Put the combined name and the other halves' books on every split
    order in a list, in one query for the whole page."""
    groups = {o.split_group for o in orders if o.split_group}
    if not groups:
        return
    by_group = {}
    for half in (Order.objects.filter(split_group__in=groups)
                 .select_related("current_account__book").order_by("pk")):
        by_group.setdefault(half.split_group, []).append(half)
    for order in orders:
        halves = by_group.get(order.split_group) if order.split_group else None
        if not halves or len(halves) < 2:
            continue
        order.combined_number = combined_number(halves)
        order.split_other_books = [
            getattr(order_book(h), "name", "") for h in halves if h.pk != order.pk]


def other_halves_for_page(order, member):
    """The other halves of `order`, dressed for its page: lines in the same
    order the page lists its own, with the rolls scanned for each, the
    half's totals, and whether the viewer may open it."""
    from decimal import Decimal
    from .views import _order_item_variant_lines

    halves = []
    for half in split_halves(order):
        if half.pk == order.pk:
            continue
        items = sorted(
            half.items.select_related("product", "product_variant"),
            key=lambda i: ((getattr(i.product, "title", "") or "").casefold(),
                           (getattr(i.product_variant, "variant_sku", "") or ""), i.pk))
        held = {}
        for r in half.stock_reservations.all():
            if r.order_item_id:
                held.setdefault(r.order_item_id, []).append(r)
        for it in items:
            rs = held.get(it.pk, [])
            it.scanned_count = len(rs)
            it.scanned_meters = sum((r.quantity or Decimal("0") for r in rs), Decimal("0"))
            it.variant_lines = _order_item_variant_lines(it)
        half.page_items = items
        half.book_name = getattr(order_book(half), "name", "")
        half.may_open = member_can_use_book(member, order_book(half))
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
