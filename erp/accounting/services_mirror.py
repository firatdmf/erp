"""Inter-company mirror: one debt, kept once, shown in both books.

Laleli and Ergene each keep an account for the other. Entered by hand, the
two halves of the same debt drifted 14,197.35 apart before anyone looked,
and closing that took a line-by-line pass over three years of both ledgers.
A pair removes the second entry altogether: whatever is posted on one
account — a payment, an invoice, a transfer, an adjustment — is written
onto the other with the opposite sign, and kept in step when it changes.

The mirror is a plain `intercompany` row, not a copy of the document. A
payment Laleli makes is not a payment in Ergene's book: no cash moved
there, so it must not reach a cash box or the payments list, and an
invoice must not post stock twice. The row carries the value and points
back at the original, and that is all.

Its dollar value is the original's `amount_base` negated, in the original's
currency and rate, so the two accounts cannot differ by a conversion.

A mirror is changed only through its original. `CurrentAccountMovement.save`
and `.delete` refuse a mirror row unless the `_mirror_sync` flag set here is
on it, and deleting the original removes the mirror by CASCADE.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models_accounts import CurrentAccount, CurrentAccountMovement

DESCRIPTION_MAX = CurrentAccountMovement._meta.get_field("description").max_length
REFERENCE_MAX = CurrentAccountMovement._meta.get_field("reference").max_length


def _describe(original):
    text = f"Mirror of {original.book.name}: {original.description or original.get_movement_type_display()}"
    return text[:DESCRIPTION_MAX]


def is_mirrored(movement):
    """Whether this movement should have a counterpart on the paired account."""
    if movement.mirror_of_id:
        return False                          # a mirror is never mirrored back
    account = movement.current_account
    partner = account.mirror_account
    if partner is None or account.mirror_since is None:
        return False
    return movement.created_at is not None and movement.created_at >= account.mirror_since


def sync_mirror(movement):
    """Create or refresh the counterpart of `movement`. Returns it, or None."""
    if not is_mirrored(movement):
        return None
    partner = movement.current_account.mirror_account

    mirror = CurrentAccountMovement.objects.filter(mirror_of=movement).first()
    if mirror is None:
        mirror = CurrentAccountMovement(mirror_of=movement, movement_type="intercompany",
                                        created_by=movement.created_by)
    mirror.current_account = partner
    mirror.book = partner.book
    mirror.date = movement.date
    mirror.due_date = movement.due_date
    mirror.amount = -movement.amount
    mirror.currency = movement.currency
    mirror.exchange_rate = movement.exchange_rate
    # Set explicitly: save() only derives it when it is empty, and the
    # published rate for the day is not necessarily the one the original used.
    mirror.amount_base = -movement.amount_base
    mirror.is_void = movement.is_void
    mirror.description = _describe(movement)
    mirror.reference = (movement.reference or "")[:REFERENCE_MAX]
    # The flag is lifted straight after: Django caches this instance on the
    # original (original.mirror), and a flag left on it would let a later
    # save of that same object slip past the lock.
    mirror._mirror_sync = True
    try:
        mirror.save()
    finally:
        del mirror._mirror_sync
    return mirror


@transaction.atomic
def pair_accounts(first, second, since=None):
    """Pair two accounts in different books. Returns the moment mirroring starts.

    Movements already on either account are left alone: pairing is for
    accounts whose history has been reconciled, and copying it would count
    every row twice.
    """
    if first.pk == second.pk:
        raise ValidationError("An account can't be paired with itself.")
    if first.book_id == second.book_id:
        raise ValidationError("A pair must be two accounts in different books.")
    for account, other in ((first, second), (second, first)):
        if account.mirror_account_id not in (None, other.pk):
            raise ValidationError(f"{account} is already paired with another account.")
    since = since or timezone.now()
    CurrentAccount.objects.filter(pk=first.pk).update(mirror_account=second, mirror_since=since)
    CurrentAccount.objects.filter(pk=second.pk).update(mirror_account=first, mirror_since=since)
    for account, other in ((first, second), (second, first)):
        account.mirror_account, account.mirror_since = other, since
    return since
