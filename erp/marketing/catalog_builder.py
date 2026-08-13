"""Turn a Product queryset into the page/block structure the catalog renders.

This is the seam between "which products" (a queryset the caller chooses) and
"how they look" (marketing/templates/marketing/catalog/page.html). Nothing
here knows about WeasyPrint; nothing in the template knows about models.

Block shape is inferred from the variants, mirroring the two shapes the
printed reference catalog actually uses:

  - variants priced DIFFERENTLY  → one row per variant with its own price,
    like the fitted bed sheet's size list.
  - variants priced the SAME     → a single price plus a "Colors: …" line,
    like the table cloth and bath mats.

Prices are rendered from whatever is on the record today. The markup-on-cost
pricing is deliberately NOT here yet: marketing.Product.cost is empty for
every featured product (checked across all 55), so cost has to come from the
warehouse side before a markup means anything.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

# Blocks per page. Three is what the reference catalog fits on an A4 page at
# this type size; more than that overflows the sheet.
BLOCKS_PER_PAGE = 3

# Attributes that describe what the product IS, in the order they should read
# ("Cotton sateen, 300 cm, high gsm"). Order here is the printed order, so the
# spec line does not shuffle between products.
#
# Deliberately excluded: warranty / fast_shipping / wrinkle_resistance. They
# are the three most common attributes in the data but they are sales flags,
# not composition, and they crowd out the spec the buyer is looking for.
SPEC_ATTRIBUTES = (
    "material", "composition", "fabric_type", "texture", "sheet type",
    "width", "weight", "gsm", "sheerness_level", "number_of_panels", "header",
)
MAX_SPEC_PARTS = 3


def _prettify(text) -> str:
    """'fabric_type' → 'Fabric type', 'semi sheer' → 'Semi sheer'."""
    cleaned = str(text or "").replace("_", " ").replace("-", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else ""


# Costs are held in USD — 1,189 of 1,191 warehouse rows and every ready-made
# cost are USD, and there is no currency column anywhere in marketing/models.py
# to say otherwise. USD is therefore the invariant the catalog computes in; a
# catalog only converts on the way OUT, when it is quoted to a euro buyer.
BASE_CURRENCY = "USD"
CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "TRY": "₺", "GBP": "£"}


def _money(amount, currency: str = BASE_CURRENCY) -> str:
    """2.4700 → '$2.47'; whole numbers stay whole, as in the reference."""
    if amount is None:
        return ""
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value == value.to_integral_value():
        return f"{symbol}{value.to_integral_value()}"
    return f"{symbol}{value}"


def _photo_for(product) -> str | None:
    """Primary image, falling back to the first image file on the product."""
    if product.primary_image_id and product.primary_image.file_url:
        return product.primary_image.file_url
    for file in product.files.all():
        if file.file_type == "image" and file.file_url:
            return file.file_url
    return None


def _spec_part(name: str, value: str) -> str:
    """One spec fragment, named only when the value cannot speak for itself.

    'Cotton sateen' is self-describing; the bare '3' stored under
    number_of_panels is not, and printing it alone gives specs that read
    '3, 2, Rod pocket'. Numeric values therefore keep their attribute name.
    """
    pretty = _prettify(value)
    if not pretty:
        return ""
    if pretty.replace(".", "", 1).isdigit():
        return f"{_prettify(name)}: {pretty}"
    return pretty


def _spec_line(product) -> str:
    """The grey line under the heading — '80% Cotton, 20% Polyester, …'."""
    found = {}
    for attribute in product.attributes.all():
        name = (attribute.name or "").lower()
        if name in SPEC_ATTRIBUTES and name not in found:
            found[name] = _spec_part(name, attribute.value)
    ordered = [found[name] for name in SPEC_ATTRIBUTES if found.get(name)]
    return ", ".join(ordered[:MAX_SPEC_PARTS])


# Plural headings for the axes worth pluralising. Anything else prints its
# own name verbatim — blindly appending "s" turned "size per panel" into
# "Size per panels" and "width x height (per panel)" into worse.
DIMENSION_LABELS = {"color": "Colors", "colour": "Colours", "size": "Sizes"}


def _dimension_label(name: str) -> str:
    return DIMENSION_LABELS.get(name, _prettify(name))


def _variant_values(variant) -> dict:
    """{'size': '130 x 210 cm', 'color': 'White'} for one variant."""
    return {
        (value.product_variant_attribute.name or "").lower():
            _prettify(value.product_variant_attribute_value)
        for value in variant.product_variant_attribute_values.all()
    }


def _dimensions(variants) -> dict:
    """Attribute name → the distinct values across these variants, in order.

    Variants vary along more than one axis (colour AND size), so the catalog
    has to describe the axes separately — 'Sizes: …' / 'Colors: …'. Listing
    the variants themselves would print the cartesian product, which is how
    a 4-size 5-colour product turns into an unreadable 20-item line.
    """
    dimensions: dict[str, list] = {}
    for variant in variants:
        for name, value in _variant_values(variant).items():
            if not value:
                continue
            seen = dimensions.setdefault(name, [])
            if value not in seen:
                seen.append(value)
    return dimensions


def _variant_label(variant, varying: set) -> str:
    """A row label built only from the attributes that actually DIFFER.

    An attribute every variant shares ('Rod pocket' on all eight) carries no
    information in a price row and just crowds the line out.
    """
    values = _variant_values(variant)
    parts = [values[name] for name in values if name in varying and values[name]]
    return " / ".join(parts)


class Pricing:
    """How a catalog turns a product into a printed number.

    markup=None keeps whatever price is stored on the record. Give it a
    percentage and the price is derived from COST instead — one rate for the
    whole document, which is how a price list is actually revised.

    Cost is USD by definition (see BASE_CURRENCY). `fx` converts on the way
    out and is fetched ONCE per catalog, not per product, so every line on a
    sheet is quoted at the same rate.
    """

    def __init__(self, currency: str = BASE_CURRENCY, markup=None, fx=None):
        self.currency = (currency or BASE_CURRENCY).upper()
        self.markup = None if markup is None else Decimal(str(markup))
        self.fx = Decimal(str(fx)) if fx is not None else self._rate()

    def _rate(self) -> Decimal:
        if self.currency == BASE_CURRENCY:
            return Decimal("1")
        try:
            from accounting.services import get_exchange_rate
            rate = get_exchange_rate(BASE_CURRENCY, self.currency)
            if rate:
                return Decimal(str(rate))
        except Exception:
            pass
        # Quoting at a made-up rate is worse than not quoting: refuse rather
        # than silently print USD numbers under a euro sign.
        raise ValueError(
            f"No {BASE_CURRENCY}->{self.currency} exchange rate available; "
            f"cannot price this catalog."
        )

    def of(self, cost, stored_price):
        """The printed amount for one line, or None if it cannot be priced."""
        if self.markup is None:
            base = stored_price
        else:
            base = None if cost is None else Decimal(str(cost)) * (1 + self.markup / 100)
        if base is None:
            return None
        return (Decimal(str(base)) * self.fx).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_block(product, photo_side: str, pricing: "Pricing | None" = None) -> dict:
    """One product → one catalog block."""
    pricing = pricing or Pricing()
    variants = [v for v in product.variants.all() if v.variant_featured]
    for variant in variants:
        variant.catalog_price = pricing.of(variant.variant_cost, variant.variant_price)
    priced = [v for v in variants if v.catalog_price is not None]
    distinct_prices = {v.catalog_price for v in priced}

    dimensions = _dimensions(variants)
    # An axis with a single value is a property of the product, not a choice.
    varying = {name for name, values in dimensions.items() if len(values) > 1}

    block = {
        "kind": "list",
        "title": product.title or product.sku or "",
        "spec": _spec_line(product),
        "photo": _photo_for(product),
        "photo_side": photo_side,
        "rows": [],
        "notes": [],
    }

    if len(distinct_prices) > 1:
        # Genuinely different prices per variant — one row each, with prices.
        block["rows"] = [
            {"label": _variant_label(v, varying) or v.variant_sku,
             "amount": _money(v.catalog_price, pricing.currency)}
            for v in sorted(priced, key=lambda v: v.catalog_price)
        ]
        # A long list of SHORT rows reads better in two columns (the
        # reference does this for mattress protectors). Long labels — which
        # happen when a product is priced across three axes at once — just
        # wrap badly in a half-width column, so keep those single-column.
        longest = max((len(row["label"]) for row in block["rows"]), default=0)
        block["columns"] = len(block["rows"]) > 6 and longest <= 24
        return block

    # One price for the whole product: state it once, then describe each axis
    # of choice on its own line.
    price = distinct_prices.pop() if distinct_prices else pricing.of(product.cost, product.price)
    if price is not None:
        block["rows"] = [{"label": "Price:", "amount": _money(price, pricing.currency)}]
        # A lone price is a statement, not a list — the reference prints it
        # as plain "Price: $1.95" with no bullet.
        block["plain"] = True
    block["notes"] = [
        f"{_dimension_label(name)}: {', '.join(values)}"
        for name, values in dimensions.items() if len(values) > 1
    ]
    return block


def build_pages(products, *, section: str = "", kicker: str = "CATALOG",
                meta_top: str = "HOME TEXTILES", meta_bottom: str = "",
                pricing: "Pricing | None" = None) -> list[dict]:
    """A product iterable → the `pages` structure the template expects.

    Photo side alternates across the whole document (not per page) so the
    zig-zag reads continuously the way the reference catalog does.
    """
    pricing = pricing or Pricing()
    blocks = [
        build_block(product, "right" if index % 2 else "left", pricing)
        for index, product in enumerate(products)
    ]

    pages = []
    for start in range(0, len(blocks), BLOCKS_PER_PAGE):
        pages.append({
            "kicker": kicker,
            "section": section,
            "meta_top": meta_top,
            "meta_bottom": meta_bottom,
            # The wordmark belongs on the first sheet only; repeating it on
            # every page would push a block off each one.
            "show_masthead": start == 0,
            "blocks": blocks[start:start + BLOCKS_PER_PAGE],
            "note": "",
        })
    return pages


def catalog_queryset(*, limit: int | None = None, order: str = "title", category: str = ""):
    """The products a catalog is built from.

    featured=True is not a nicety, it is the whole filter: 919 of the 974
    products are hidden rows that catalog_sync creates from warehouse roll
    scans. They carry the largest quantities in the table, so ordering by
    quantity WITHOUT this filter returns fabric-roll aggregates that have no
    price and no photo — see the module docstring in catalog_sync.py.

    limit defaults to None — ALL matching products. A catalog that quietly
    stops at N is worse than a long one: you would ship a category with
    products missing and nothing would say so.

    Ordering defaults to title, not quantity: quantity is null on most
    finished goods (all but one ready-made curtain, for instance), and
    ordering by a mostly-null column puts the catalog in arbitrary order.
    """
    from .models import Product

    queryset = (
        Product.objects.filter(featured=True)
        .select_related("category", "primary_image")
        .prefetch_related(
            "attributes",
            "files",
            "variants__product_variant_attribute_values__product_variant_attribute",
        )
    )
    if category:
        queryset = queryset.filter(category__name=category)
    queryset = queryset.order_by(order)
    return queryset[:limit] if limit else queryset
