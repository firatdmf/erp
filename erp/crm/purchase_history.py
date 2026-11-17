"""What we have bought from a CRM record, for its page's Purchase history.

A company or contact is a supplier because we buy from it, not because of
the kind of record it is (CR14 retired the Supplier record, 2026-11-17):
whoever has purchases on one of their accounts shows them, beside the
orders they placed with us.
"""
from .models import of_books_in_reach


def purchase_history(**account_filter):
    """Up to 25 purchases (and purchase returns) on the accounts matching
    `account_filter` — e.g. contact=c — newest first, in the books the
    viewer may see. Cancelled ones are not part of what we bought, so they
    are left out. Each carries `pill`, the order-status colour of its row."""
    from accounting.models_accounts import Invoice

    filters = {f"current_account__{k}": v for k, v in account_filter.items()}
    purchases = list(
        of_books_in_reach(Invoice.objects.filter(
            type__in=("purchase", "purchase_return"), **filters,
        ).exclude(status="cancelled"))
        .select_related("book", "currency")
        .order_by("-date", "-id")[:25]
    )
    # Blue while it is on its way, green once received.
    pill = {"ordered": "scheduled", "received": "confirmed"}
    for inv in purchases:
        inv.pill = pill.get(inv.status, "scheduled")
    return purchases
