"""Template helpers for the operating app."""
from django import template

register = template.Library()

# WarehouseProduct.purchase_currency is a plain code (see its CURRENCY_CHOICES),
# not a link to accounting.CurrencyCategory, so the sign is mapped here rather
# than read from the database — a per-row lookup for three fixed currencies
# would cost one query per line of the stock list.
_CURRENCY_SIGNS = {
    "USD": "$",
    "EUR": "€",
    "TRY": "₺",
    "KZT": "₸",
}


@register.filter
def currency_sign(code):
    """The sign for a currency code — "$" for USD, "₺" for TRY.

    A code with no sign mapped comes back as the code itself followed by a
    NON-BREAKING space, so a currency added to the choices later still reads
    ("GBP 12.00") instead of vanishing, and never wraps away from its amount.
    """
    code = (code or "").strip().upper()
    if not code:
        return ""
    return _CURRENCY_SIGNS.get(code, code + " ")  # NBSP


@register.filter
def book_sign(warehouse):
    """The currency sign stock in this warehouse is costed in.

    A roll's unit_cost_base is held in the base currency of the book that
    owns its warehouse, so that book decides the sign — not the SKU's
    purchase_currency, which describes what a supplier once invoiced. A
    combined (ortak) warehouse lists rows from members that may sit in
    different books, so the sign is resolved per ROW here rather than once
    for the page.

    A book with no base currency yields "" — the amount then prints bare
    rather than wearing somebody else's currency.
    """
    book = getattr(warehouse, "accounting_book", None)
    currency = getattr(book, "base_currency", None)
    return currency_sign(getattr(currency, "code", "") or "")


@register.filter
def cost_in_base(value, order):
    """A cost or profit on an order, said in base first: "$10.00 (₸5,200.00)".

    Costs are kept in base and the book reports in it, so that is the
    figure that means something; the order's own currency follows in
    brackets, to set against its prices. An order in base reads as before.
    The rate is the order's (Order.rate_to_base): today's while it is
    open, the one fixed when it completed after that.
    """
    from decimal import Decimal
    from django.template.defaultfilters import floatformat
    from django.utils.html import format_html
    from operating.models import _dollar_labels

    amount = Decimal(str(value or 0))
    base_code, base_symbol = _dollar_labels()
    own = f"{order.currency_symbol}{floatformat(amount, '2g')}"
    rate = order.rate_to_base() if order.currency_code != base_code else None
    if not rate or rate == Decimal("1"):
        return own                  # in base already, or no rate to say it with
    in_base = (amount * Decimal(str(rate))).quantize(Decimal("0.01"))
    return format_html('{}{} <span class="od-in-cur">({})</span>',
                       base_symbol, floatformat(in_base, "2g"), own)


@register.filter
def photos_json(files):
    """Photos and videos as JSON for the photo viewer
    (partials/_photo_viewer.html), in the order given:
    [{"src": …, "alt": …}], a video with "video": true and its "poster".
    Autoescape makes it safe inside an attribute."""
    import json
    from marketing.product_images import is_video
    out = []
    for f in files or ():
        if not f.file_url:
            continue
        one = {"src": f.file_url, "alt": f.alt_text or ""}
        if is_video(f):
            one.update(video=True, poster=f.video_thumbnail or "")
        out.append(one)
    return json.dumps(out)


@register.filter
def thumb_src(f):
    """What a small picture of `f` shows: the photo, or a video's first
    frame ("" when it has none yet)."""
    from marketing.product_images import is_video
    if not f:
        return ""
    return (f.video_thumbnail or "") if is_video(f) else (f.file_url or "")


@register.filter
def variant_gallery(variant):
    """A catalog variant's own photos and videos, in the storefront's order
    (from variant_photos_prefetch). Never its product's: they would show
    a colour the row does not hold."""
    from marketing.product_images import storefront_gallery
    if not variant:
        return []
    files = getattr(variant, "own_files", None)
    return storefront_gallery(variant.files.all() if files is None else files, variant.pk)


@register.filter
def line_gallery(item):
    """An order line's photos and videos: its variant's own, in the
    storefront's order. A variant with none shows none — never its
    product's, which would show a colour the line does not hold. A line
    with no variant shows what the product page shows with none chosen."""
    from marketing.product_images import storefront_gallery
    if not item.product_id:
        return []
    if not item.product_variant_id:
        return storefront_gallery(item.product.files.all())
    return variant_gallery(item.product_variant)


@register.filter
def country_name(value):
    """ "TR" → "Türkiye" (in the reader's language); a typed name as it is.
    See operating/countries.py."""
    from operating.countries import country_name as name
    return name(value)


@register.simple_tag
def country_choices():
    """(code, name) for every country, for a country <select>."""
    from operating.countries import country_choices as choices
    return choices()


@register.filter
def wrap_at_plus(value):
    """Escape `value` and let a line break after each "+". Names that join
    their parts with "+" have no spaces, so without this the longest one
    sets its column's width and pushes the table past the page."""
    from django.utils.html import escape
    from django.utils.safestring import mark_safe
    return mark_safe(escape(value or "").replace("+", "+<wbr>"))


@register.simple_tag
def line_roll_groups(item):
    """A line's rolls for the order page, grouped so each group says once
    what its chips share: the rolls held from stock (their warehouse when
    they all stand in one), then the rolls each supplier purchase is
    bringing (the purchase, its depot, how many and about how much). A
    chip then only carries what is its own — barcode, length, markers."""
    from decimal import Decimal
    from django.template.defaultfilters import floatformat
    from marketing import units

    def only(values):
        values = {v for v in values}
        return values.pop() if len(values) == 1 else None

    held = None
    rolls = list(getattr(item, "item_reservations", None) or []) if getattr(item, "is_tracked", False) else []
    if rolls:
        held = {
            "rolls": rolls,
            "label": getattr(item, "scanned_label", ""),
            "warehouse": only(getattr(r.warehouse_product, "warehouse", None) for r in rolls),
        }
    coming = []
    by_purchase = {}
    for e in getattr(item, "expected_rolls", None) or []:
        group = by_purchase.get(e["purchase"].pk)
        if group is None:
            group = by_purchase[e["purchase"].pk] = {"purchase": e["purchase"], "rolls": []}
            coming.append(group)
        group["rolls"].append(e)
    pack = getattr(getattr(item, "product", None), "pack_type", None) or units.DEFAULT_PACK
    for group in coming:
        n = len(group["rolls"])
        amount = sum((e["qty"] for e in group["rolls"]), Decimal("0"))
        group["label"] = f"{n} {units.pack_noun(pack, n)} · ≈ {floatformat(amount, '-2g')} {group['rolls'][0]['unit']}"
        group["warehouse"] = only(e["warehouse"] for e in group["rolls"])
    return {"held": held, "coming": coming}


@register.simple_tag
def waiting_purchase_rows(purchases, items):
    """The purchases an order waits for, each with its supplier and what it
    brings to this order ("3 rolls · ≈ 90 m"), read from the rolls its plan
    says are coming for the order's lines (attach_line_purchases)."""
    from decimal import Decimal
    from django.template.defaultfilters import floatformat
    from marketing import units

    rows = []
    for p in purchases:
        counts, amounts = {}, {}
        for it in items or []:
            coming = [e for e in (getattr(it, "expected_rolls", None) or []) if e["purchase"].pk == p.pk]
            if not coming:
                continue
            pack = getattr(getattr(it, "product", None), "pack_type", None) or units.DEFAULT_PACK
            key = (pack, coming[0]["unit"])
            counts[key] = counts.get(key, 0) + len(coming)
            amounts[key] = amounts.get(key, Decimal("0")) + sum((e["qty"] for e in coming), Decimal("0"))
        brings = " · ".join(
            f"{n} {units.pack_noun(pack, n)} · ≈ {floatformat(amounts[(pack, unit)], '-2g')} {unit}"
            for (pack, unit), n in counts.items())
        account = getattr(p, "current_account", None)
        rows.append({"purchase": p, "supplier": getattr(account, "name", ""), "brings": brings})
    return rows
