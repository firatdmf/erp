"""What a variant sells for.

A price is not typed and not stored: it is the variant's cost times its
price multiplier, worked out whenever it is read, so it follows the stock it
is sold from (decided 2026-10-15). The cost is ProductVariant.live_cost — the
weighted average of the priced stock on hand, else the variant's stored
cost. The multiplier is the product's own, else its group's, typed as a
formula ("4/3", "3") and worked out exactly. The result is rounded UP to the
next PRICE_STEP, so a price never ends in an odd cent and never comes out
under the multiplier.

A variant with no cost, or no multiplier, has no price (None): nothing is
invented.
"""
import ast
import math
import operator
from decimal import Decimal
from fractions import Fraction

PRICE_STEP = Decimal("0.05")

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv}


def parse_multiplier(text):
    """The price multiplier typed as a formula — "4/3", "3", "1.3",
    "(1+1/3)" — as an exact Fraction. Numbers, + - × ÷ and brackets only;
    anything else, or a result not above zero, raises ValueError.

    Kept as typed and worked out on every read, so 4/3 is four thirds and
    not 1.3333: $3.60 × 4/3 is $4.80, not $4.79.
    """
    text = (text or "").strip().replace(",", ".").replace("×", "*").replace("÷", "/")
    if not text:
        raise ValueError("empty")
    if len(text) > 40:
        raise ValueError("too long")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return Fraction(Decimal(str(node.value)))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("not a formula")

    try:
        value = walk(ast.parse(text, mode="eval"))
    except (SyntaxError, ZeroDivisionError) as exc:
        raise ValueError(str(exc)) from exc
    if value <= 0:
        raise ValueError("not above zero")
    return value


def multiplier_for(product):
    """What this product's cost is multiplied by to give its price: its own
    multiplier, else its group's. None when neither says — no price is
    invented. Every group must carry one (ProductCategory.price_multiplier)."""
    if product is None:
        return None
    for text in (product.price_multiplier,
                 product.category.price_multiplier if product.category_id else ""):
        if text:
            try:
                return parse_multiplier(text)
            except ValueError:
                return None
    return None


def selling_price(cost, multiplier):
    """cost × multiplier, rounded up to the next 0.05; None without a cost
    or a multiplier."""
    if cost is None or multiplier is None:
        return None
    raw = Fraction(Decimal(str(cost))) * Fraction(multiplier)
    steps = max(0, math.ceil(raw / Fraction(PRICE_STEP)))
    return (steps * PRICE_STEP).quantize(Decimal("0.01"))


def live_prices(variant_ids):
    """{variant_id: price} for these variants, in a fixed number of queries."""
    from .models import ProductVariant, attach_live_costs
    variants = attach_live_costs(
        ProductVariant.objects.filter(pk__in=list(variant_ids))
        .select_related("product__category"))
    return {v.pk: v.live_price for v in variants}


def attach_live_prices(products):
    """Give each product its from_price (its variants' lowest price) and each
    prefetched variant its cost, for a list page. Returns the list."""
    from django.db.models import prefetch_related_objects
    from .models import attach_live_costs
    products = list(products)
    prefetch_related_objects(products, "variants")
    attach_live_costs(v for p in products for v in p.variants.all())
    for p in products:
        for v in p.variants.all():
            v.product = p       # its multiplier, without a query per variant
        prices = [v.live_price for v in p.variants.all() if v.live_price is not None]
        p.from_price = min(prices) if prices else None
    return products


def book_costs(variant_ids):
    """{(variant_id, book_id): weighted-average unit cost of that book's
    stock of the variant}, valued exactly as that book's balance sheet
    carries it (services_ledger._inventory_unit_cost). One query.

    An order is billed to one book and ships off that book's shelves, so
    its price is worked out from what THAT book's stock cost — Laleli's
    rolls of a colour and Ergene's were bought separately, at their own
    prices (decided 2026-10-15).
    """
    from django.db.models import DecimalField, Sum
    from accounting.services_ledger import _inventory_line_value, _inventory_unit_cost
    from operating.models import WarehouseProductItem
    rows = (WarehouseProductItem.objects
            .filter(product__catalog_variant_id__in=list(variant_ids),
                    status__in=("in_stock", "partial"),
                    product__warehouse__accounting_book__isnull=False)
            .exclude(quantity_remaining=None)
            .annotate(_unit_cost=_inventory_unit_cost())
            .exclude(_unit_cost=None)
            .values("product__catalog_variant_id", "product__warehouse__accounting_book_id")
            .annotate(value=Sum(_inventory_line_value()),
                      quantity=Sum("quantity_remaining",
                                   output_field=DecimalField(max_digits=20, decimal_places=6))))
    return {(r["product__catalog_variant_id"], r["product__warehouse__accounting_book_id"]):
            (r["value"] / r["quantity"]).quantize(Decimal("0.0001"))
            for r in rows if r["quantity"]}


def book_price(variant, book_id, costs, shelf_cost=None):
    """What `variant` sells for on an order in book `book_id`: that book's
    stock cost marked up. Without stock in that book, the highest cost
    another book holds it at — overstating cost loses a little margin,
    understating it sells below cost. With no valued stock anywhere, the
    shelf's own figure (`shelf_cost`, when the caller has one), and last
    the variant's live price. `costs` is book_costs() for the variants."""
    mine = costs.get((variant.pk, book_id)) if book_id else None
    if mine is None:
        others = [c for (vid, _b), c in costs.items() if vid == variant.pk]
        mine = max(others) if others else None
    if mine is None:
        mine = shelf_cost
    if mine is None:
        return variant.live_price
    return selling_price(mine, multiplier_for(variant.product))
