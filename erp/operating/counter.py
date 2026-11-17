"""Money taken at the counter for a retail order, kept equal to its bill.

A retail order is paid in full when it is made (OrderPayment links the
collection). Retail Sales is a shared account with no customer behind it,
so money left over there is nobody's credit: when a retail order is
completed again after an edit, cancelled or returned, the difference is
collected or given back through the cash account that took the money.

Worked out from the payments linked to the order by key, never from text,
so settling twice finds nothing the second time — the old automatic
collection matched notes reading "ORD-<pk>" and took order 286's money
twice.
"""
from django.db import transaction


def counter_cash_account(order):
    """The latest confirmed payment linked to the order, which names the
    cash account its counter money went into — or None when it is not known."""
    last = (order.payment_links.select_related("payment__cash_account", "payment__currency")
            .filter(payment__status="confirmed").order_by("-payment__date", "-pk").first())
    if last is None or last.payment.cash_account_id is None:
        return None
    return last.payment


def settle_counter_gap(order, user):
    """Collect or give back Order.counter_gap through the cash account the
    sale went into. Returns (kind, amount, cash_account), or None when
    there is no gap or the cash account is not known.

    `user` may be a User or a Member, as apply_order_status_change takes.
    """
    from datetime import date
    from accounting.models import Payment
    from accounting.views_payment import _next_payment_number
    from erp.roles import _member_and_user
    from .models import OrderPayment

    gap = order.counter_gap()
    first = counter_cash_account(order) if gap else None
    if first is None:
        return None
    member, user = _member_and_user(user)
    difference = gap[2]
    kind = "collection" if difference > 0 else "refund_in"
    with transaction.atomic():
        pay = Payment.objects.create(
            current_account=first.current_account, book=first.book,
            number=_next_payment_number(first.book, kind),
            type=kind, method="cash", status="draft", date=date.today(),
            amount=abs(difference), currency=first.currency,
            cash_account=first.cash_account,
            description=(f"Rest collected at the counter for Order #{order.pk}" if kind == "collection"
                         else f"Given back at the counter for Order #{order.pk}"),
            notes=f"ORD-{order.pk}", created_by=member)
        OrderPayment.objects.create(order=order, payment=pay)
        pay.confirm(user=user)
    return kind, abs(difference), first.cash_account
