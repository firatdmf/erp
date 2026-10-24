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
    """A variant's photos as JSON for the warehouse photo viewer:
    [{"src": …, "alt": …}], in the order given. Autoescape makes it safe
    inside an attribute."""
    import json
    return json.dumps([{"src": f.file_url, "alt": f.alt_text or ""}
                       for f in files or ()])


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
