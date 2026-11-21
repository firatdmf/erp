"""Sell-down goals: how far a goal has come, for the person reading it.

Everything here is worked out on read. The only stored figures are the
goal's settings and each book's value on the day it joined
(SellDownGoalBook.start_value); what is on the shelves now, which designs
hold most of it and whether the pace is being kept all follow the stock.

Stock is valued as the balance sheet values it — every item still on the
floor, its remaining quantity at its own cost (WarehouseProductItem.
unit_cost_base, the owning book's base currency) — so a goal and the
warehouse pages always agree.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum
from django.utils import timezone

from .models import SellDownGoal, SellDownGoalBook, WarehouseProductItem

ON_FLOOR = ("in_stock", "partial")
ZERO = Decimal("0")
_DEC = DecimalField(max_digits=20, decimal_places=4)


def stock_items(goal, book_ids):
    """The goal's items still on the floor in these books."""
    qs = WarehouseProductItem.objects.filter(
        status__in=ON_FLOOR,
        quantity_remaining__gt=0,
        product__warehouse__accounting_book_id__in=list(book_ids),
        product__catalog_variant__isnull=False,
    )
    if goal.category_id:
        qs = qs.filter(product__catalog_variant__product__category_id=goal.category_id)
    if goal.tag:
        qs = qs.filter(product__catalog_variant__product__tags__contains=[goal.tag])
    return qs


def stock_value(goal, book_ids):
    """What the goal's stock in these books is worth now."""
    total = stock_items(goal, book_ids).aggregate(
        v=Sum(F("quantity_remaining") * F("unit_cost_base"), output_field=_DEC))["v"]
    return (total or ZERO).quantize(Decimal("0.01"))


@dataclass
class Design:
    """One catalog product's stock under the goal."""
    product_id: int
    sku: str
    title: str
    unit: str
    value: Decimal
    quantity: Decimal
    pack_type: str = ""
    share: Decimal = ZERO          # of the value left, 0–100
    running_share: Decimal = ZERO  # this one and every bigger one, 0–100
    variants: list = field(default_factory=list)  # filled by the goal page only


def designs(goal, book_ids):
    """Every product under the goal with stock, most value first."""
    rows = (stock_items(goal, book_ids)
            .values("product__catalog_variant__product",
                    "product__catalog_variant__product__sku",
                    "product__catalog_variant__product__title",
                    "product__catalog_variant__product__unit",
                    "product__catalog_variant__product__pack_type")
            .annotate(value=Sum(F("quantity_remaining") * F("unit_cost_base"),
                                output_field=_DEC),
                      quantity=Sum("quantity_remaining", output_field=_DEC))
            .order_by("-value", "product__catalog_variant__product__sku"))
    out = [Design(product_id=r["product__catalog_variant__product"],
                  sku=r["product__catalog_variant__product__sku"] or "",
                  title=r["product__catalog_variant__product__title"] or "",
                  unit=r["product__catalog_variant__product__unit"] or "",
                  value=r["value"] or ZERO,
                  quantity=r["quantity"] or ZERO,
                  pack_type=r["product__catalog_variant__product__pack_type"] or "")
           for r in rows]
    total = sum((d.value for d in out), ZERO)
    running = ZERO
    for d in out:
        running += d.value
        if total:
            d.share = d.value * 100 / total
            d.running_share = running * 100 / total
    return out


@dataclass
class Variant:
    """One variant's stock under the goal: what a design's row opens to."""
    variant_id: int
    sku: str
    value: Decimal
    quantity: Decimal
    items: int


def variants_by_design(goal, book_ids):
    """{product id: [Variant, …]} for every design under the goal, each
    design's variants most value first — one query for the whole page."""
    rows = (stock_items(goal, book_ids)
            .values("product__catalog_variant",
                    "product__catalog_variant__variant_sku",
                    "product__catalog_variant__product")
            .annotate(value=Sum(F("quantity_remaining") * F("unit_cost_base"),
                                output_field=_DEC),
                      quantity=Sum("quantity_remaining", output_field=_DEC),
                      items=Count("id"))
            .order_by("-value", "product__catalog_variant__variant_sku"))
    out = {}
    for r in rows:
        out.setdefault(r["product__catalog_variant__product"], []).append(Variant(
            variant_id=r["product__catalog_variant"],
            sku=r["product__catalog_variant__variant_sku"] or "",
            value=r["value"] or ZERO,
            quantity=r["quantity"] or ZERO,
            items=r["items"]))
    return out


def focus(all_designs, percent):
    """The fewest designs, biggest first, that hold `percent` of the value."""
    picked = []
    for d in all_designs:
        picked.append(d)
        if d.running_share >= percent:
            break
    return picked


@dataclass
class Progress:
    """A goal as one reader sees it: the books they work in, together."""
    goal: SellDownGoal
    books: list
    start_value: Decimal
    target_value: Decimal
    value_now: Decimal
    designs: list
    focus: list
    quantities: list = field(default_factory=list)  # [(unit, total)], biggest first
    today: date = None

    @property
    def sold_value(self):
        return max(self.start_value - self.value_now, ZERO)

    @property
    def to_sell(self):
        """How much value the goal asks to see go, start to deadline."""
        return max(self.start_value - self.target_value, ZERO)

    @property
    def done_percent(self):
        """How far along the goal is, 0–100."""
        if not self.to_sell:
            return Decimal("100")
        return min(max(self.sold_value * 100 / self.to_sell, ZERO), Decimal("100"))

    @property
    def time_percent(self):
        """How much of the time from start to deadline has gone, 0–100."""
        days = (self.goal.deadline - self.goal.start_date).days
        if days <= 0:
            return Decimal("100")
        gone = (self.today - self.goal.start_date).days
        return min(max(Decimal(gone) * 100 / days, ZERO), Decimal("100"))

    @property
    def expected_value(self):
        """Where the value should be today on a straight line from the
        start to the target at the deadline."""
        return self.start_value - self.to_sell * self.time_percent / 100

    @property
    def behind_by(self):
        """Value above the line: positive is behind pace, negative ahead."""
        return self.value_now - self.expected_value

    @property
    def on_pace(self):
        return self.behind_by <= 0

    @property
    def days_left(self):
        return max((self.goal.deadline - self.today).days, 0)

    @property
    def needed_per_month(self):
        """Value to sell each month from now to make the deadline."""
        left = self.value_now - self.target_value
        if left <= 0:
            return ZERO
        months = Decimal(self.days_left) / Decimal("30.44")
        return left / months if months > 0 else left

    @property
    def reached(self):
        return self.value_now <= self.target_value


def progress(goal, book_ids, today=None):
    """The goal over the books in `book_ids` it covers, or None when the
    reader works in none of them."""
    parts = list(SellDownGoalBook.objects.filter(goal=goal, book_id__in=list(book_ids))
                 .select_related("book").order_by("book__name"))
    if not parts:
        return None
    ids = [p.book_id for p in parts]
    start = sum((p.start_value for p in parts), ZERO)
    target = (start * goal.target_left_percent / 100).quantize(Decimal("0.01"))
    rows = designs(goal, ids)
    now = sum((d.value for d in rows), ZERO).quantize(Decimal("0.01"))
    by_unit = {}
    for d in rows:
        by_unit[d.unit] = by_unit.get(d.unit, ZERO) + d.quantity
    return Progress(
        goal=goal, books=[p.book for p in parts],
        start_value=start, target_value=target, value_now=now,
        designs=rows, focus=focus(rows, goal.focus_percent),
        quantities=sorted(by_unit.items(), key=lambda kv: -kv[1]),
        today=today or timezone.localdate(),
    )


def readable_book_ids(member):
    from accounting.services_accounts import member_books
    return list(member_books(member).values_list("pk", flat=True))


def progress_for(member, goals=None, today=None):
    """Every active goal this member works in, as they see it."""
    book_ids = readable_book_ids(member)
    if not book_ids:
        return []
    goals = goals if goals is not None else SellDownGoal.objects.filter(
        is_active=True, book_parts__book_id__in=book_ids).distinct()
    out = []
    for goal in goals:
        p = progress(goal, book_ids, today=today)
        if p is not None:
            out.append(p)
    return out


def set_books(goal, books):
    """Make `books` the goal's books. A book joining records what its
    stock is worth now; a book leaving takes its start value with it;
    a book staying keeps the value it started with."""
    wanted = {b.pk for b in books}
    SellDownGoalBook.objects.filter(goal=goal).exclude(book_id__in=wanted).delete()
    have = set(SellDownGoalBook.objects.filter(goal=goal).values_list("book_id", flat=True))
    for book_id in wanted - have:
        SellDownGoalBook.objects.create(
            goal=goal, book_id=book_id, start_value=stock_value(goal, [book_id]))
