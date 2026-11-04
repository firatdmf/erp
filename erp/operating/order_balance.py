"""The customer's balance, as an order sheet prints it under its total.

    Previous balance         $1,180.50
    This order               $4,250.00
    Balance due              $5,430.50

"Previous" is everything on the customer's account EXCEPT the sale rows
these orders wrote. A sale only reaches the account when the order ships
(see accounting.services_accounts.post_order_movement), so the plain
balance would leave an open order out and fold a shipped one into
"previous" — the same sheet would add up differently the day it ships.
Taking the orders' own rows out makes both read the same. Payments taken
against the order are not sale rows, so they stay in "previous" and are
counted.

"Previous" is what the customer owes across every book the person
printing may see, not only the book the order bills: the customer owes
the business, and a sheet quoting Laleli's account alone tells them a
figure that leaves their Ergene debt out. The sheet prints the sum
alone, naming no book — the customer owes one business, and a
white-label sheet would say who sent it; `books` carries the parts for
anyone who wants them. Books the person cannot see are not counted; with nobody printing (no member) only the accounts the orders
bill are counted.

One block per currency: accounts are added only when they are kept in
the same currency, since a balance converted at today's rate is not what
the customer owes in either. A block with none of the sheet's orders in
it is not printed — "This order" would read 0.00 under it.

Figures are in the account's currency — what the customer owes is stated
in what they are billed in. An order priced in another currency is
converted into it; where no rate can be had the block is left out
rather than printed with a wrong figure in it.

Nothing prints for a balance that comes to zero, nor for an order with
no customer on it: a walk-in sale posts to the shared retail account,
whose balance is the shop's, not the person holding the sheet.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

CENT = Decimal("0.01")


def _has_customer(order):
    return bool(order.contact_id or order.company_id or order.web_client_id)


def _base_currency():
    from accounting.models import CurrencyCategory
    code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
    return CurrencyCategory.objects.filter(code=code).first()


def _in_account_currency(order, amount, currency, base_code):
    """`amount` in `order`'s currency, restated in `currency`, or None."""
    if order.currency_code == currency.code:
        return amount
    base = order.to_base(amount)
    if currency.code == base_code:
        return base
    from django.utils import timezone
    from accounting.services import get_exchange_rate
    rate = get_exchange_rate(base_code, currency.code, on_date=timezone.localdate())
    if not rate:
        return None
    return (base * Decimal(str(rate))).quantize(CENT, rounding=ROUND_HALF_UP)


def _previous_balance(account, orders, currency, base_code):
    """The account's balance without `orders`' own sale rows, or None."""
    from accounting.services_accounts import ORDER_MOVEMENT_TYPES
    from .models import Order

    own = account.movements.live().filter(
        source_type=ContentType.objects.get_for_model(Order),
        source_id__in=[o.pk for o in orders],
        movement_type__in=ORDER_MOVEMENT_TYPES,
    )
    if currency.code == base_code:
        # cached_balance is the base sum of the live rows — recompute_balance.
        rows = sum((m.amount_base for m in own), Decimal("0.00"))
        return account.cached_balance - rows
    balance = account.own_currency_balance()
    if balance is None:
        return None
    for movement in own:
        amount, _rate = account.in_own_currency(movement)
        if amount is None:
            return None
        balance -= amount
    return balance


def _customer_accounts(account, member):
    """The current accounts of `account`'s customer in the books `member`
    may see, `account` itself among them."""
    from accounting.models import CurrentAccount
    from accounting.services_accounts import member_books

    for field in ("contact_id", "company_id", "supplier_id"):
        value = getattr(account, field)
        if value:
            return list(CurrentAccount.objects
                        .filter(book__in=member_books(member), **{field: value})
                        .exclude(pk=account.pk)
                        .select_related("book", "default_currency")
                        .order_by("book__name"))
    return []


def order_balances(orders, totals, member=None):
    """What the customer owes, before and after `orders`, in each currency
    their accounts are kept in.

    `totals` maps an order's pk to the total the sheet prints for it, in
    the order's own currency — the figure "This order" adds is the one
    printed above it, so the sheet adds up on its face. `member` is who is
    printing: their books decide which of the customer's other accounts
    are counted.

    Returns a list of dicts, one per currency, in the orders' own order:
    account (the first one the orders bill), books (each counted
    account's previous balance, as {account, previous}), currency_code,
    symbol, previous, this_orders, after. Empty when nothing is owed
    either way.
    """
    base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
    by_account = {}
    for order in orders:
        if order.current_account_id and _has_customer(order):
            by_account.setdefault(order.current_account_id, []).append(order)

    # Every account counted, the orders' own first, each under its currency.
    accounts = [os[0].current_account for os in by_account.values()]
    for account in list(accounts):
        for other in _customer_accounts(account, member):
            if all(other.pk != a.pk for a in accounts):
                accounts.append(other)
    by_currency = {}
    for account in accounts:
        currency = account.own_currency or _base_currency()
        if currency is not None:
            by_currency.setdefault(currency.code, (currency, []))[1].append(account)

    balances = []
    for currency, currency_accounts in by_currency.values():
        billed = [o for a in currency_accounts for o in by_account.get(a.pk, [])]
        if not billed:
            continue
        books = []
        for account in currency_accounts:
            previous = _previous_balance(account, billed, currency, base_code)
            if previous is None:
                books = None
                break
            books.append({"account": account, "previous": previous})
        if books is None:
            continue
        this_orders = Decimal("0.00")
        for order in billed:
            amount = _in_account_currency(
                order, Decimal(str(totals.get(order.pk) or 0)), currency, base_code)
            if amount is None:
                this_orders = None
                break
            this_orders += amount
        if this_orders is None:
            continue
        previous = sum((b["previous"] for b in books), Decimal("0.00"))
        after = previous + this_orders
        if after.quantize(CENT) == 0:
            continue
        # What the sum is made of: only accounts holding something, and
        # none at all when a single one does — it is the sum.
        held = [b for b in books if b["previous"].quantize(CENT) != 0]
        balances.append({
            "account": currency_accounts[0],
            "books": held if len(held) > 1 else [],
            "currency_code": currency.code,
            "symbol": currency.symbol or currency.code,
            "previous": previous,
            "this_orders": this_orders,
            "after": after,
        })
    return balances
