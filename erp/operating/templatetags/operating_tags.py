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
