"""The sell-down card on the dashboard (operating.sell_down)."""
from django import template

from marketing.units import unit_short

register = template.Library()

# Designs named on the card; the goal's page lists the rest.
CARD_DESIGNS = 6


@register.inclusion_tag("operating/partials/sell_down_card.html")
def sell_down_card(member):
    """Every active goal in a book this member works in, read over their
    books. Money only for those who read cost; a sales rep sees shares,
    quantities and designs."""
    from erp.roles import is_sales_rep

    from operating import sell_down
    from operating.views_sell_down import _currency_symbol

    goals = sell_down.progress_for(member) if member is not None else []
    return {
        "goals": [(p, _currency_symbol(p), p.focus[:CARD_DESIGNS]) for p in goals],
        "show_money": member is not None and not is_sales_rep(member),
    }


@register.filter
def sd_money(value, symbol=""):
    """A whole amount with its currency symbol: "$568,597"."""
    try:
        number = round(value)
    except (TypeError, ValueError):
        return ""
    sign = "-" if number < 0 else ""
    return f"{sign}{symbol}{abs(number):,}"


@register.filter
def sd_qty(quantity, unit):
    """A whole-number quantity with its unit: "145,622 m"."""
    try:
        number = f"{round(quantity):,}"
    except (TypeError, ValueError):
        return ""
    return f"{number} {unit_short(unit)}".strip()
