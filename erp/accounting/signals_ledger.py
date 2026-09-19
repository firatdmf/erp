"""Posting to the general ledger as things happen, rather than in a batch.

The ledger balances by construction, and until now that was the only thing
it did reliably: entries arrived through `backfill_ledger`, a command
somebody ran by hand against one book. Ergene got 87 entries that way and
Laleli got none, and from the moment each run finished the ledger began
going stale — every movement typed afterwards changed what the accounts
owed without changing the ledger that is supposed to summarise them.

So the batch was never the mechanism. It was a snapshot of one, and the gap
between snapshots is exactly where the $1.67M went the first time.

These receivers close it. Every path that writes a current account movement
or a cash row — the payment form, invoice issue, warehouse intake, the
inter-company mirror, an import command, a shell one-liner — goes through
`Model.save()`, so hanging the posting there covers all of them at once and
covers the ones nobody has written yet. It is the same argument
signals_accounts makes for mirroring movements into Payment rows, for the
same reason: a rule enforced at one call site is a rule that holds until
someone adds a second call site.

Two things this must never do:

  It must never refuse the save. A posting rule that cannot decide its
  contra is a bookkeeping question, not a reason the operator cannot record
  a payment. Failures are logged and the business write stands — and because
  post_movement and post_cash_entry are atomic, a failure rolls itself back
  to its savepoint and leaves nothing half-written behind.

  It must never post twice. Both posting functions replace what they find
  for the same source rather than adding to it, so a re-save, a resync and
  a repeated backfill all converge on one entry.

Stock is here too: the cost of what leaves the shelves becomes cost of
goods sold as it goes, so a sale no longer shows its revenue against no
cost at all.

What still does NOT post live: cash rows whose source is a transfer or a
currency exchange, which move cash on both legs and need an entry shaped by
hand; Payment's own cash row, which is deliberately left to the
current-account movement that already carries it; and stock ARRIVING,
which is the purchase invoice's job (see services_posting).
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CashTransactionEntry
from .models_accounts import CurrentAccountMovement

log = logging.getLogger("accounting.ledger")


def _safely(what, action, *args, **kwargs):
    """Run a posting call, absorbing anything it raises.

    The caller is in the middle of saving a business record and has no way
    to handle a bookkeeping problem, so the problem is logged with enough
    detail to find the row again and the save goes through. Deliberately
    broad: a chart account missing on a fresh database, a movement type
    nobody has decided, a source whose content object has been deleted out
    from under its cash row — none of them should stop an operator working.
    """
    try:
        return action(*args, **kwargs)
    except Exception as exc:
        log.warning("Ledger posting skipped for %s: %s", what, exc)
        return None


# ---------------------------------------------------------------------------
# Current account movements
# ---------------------------------------------------------------------------
@receiver(post_save, sender=CurrentAccountMovement)
def post_movement_to_ledger(sender, instance, raw=False, **kwargs):
    """Post, repost or withdraw this movement's entry.

    Fires on create AND update because post_movement is idempotent and an
    update is the case that matters most: resync_posted_movement re-saves
    the very same row when a payment's amount or rate is corrected, and
    without this the ledger would keep the figure that was corrected away.

    Voiding is an update too. A void row belongs in no balance, so
    post_movement withdraws its entry rather than writing one, which is why
    cancelling a document does not need a receiver of its own.
    """
    if raw:                     # loaddata: the fixture is the truth, not us
        return
    from .services_posting import post_movement
    _safely(f"movement {instance.pk}", post_movement, instance)


@receiver(post_delete, sender=CurrentAccountMovement)
def unpost_movement_from_ledger(sender, instance, **kwargs):
    """A deleted movement takes its entry with it.

    Cascades come through here too — deleting an original removes its
    mirror by CASCADE, and the mirror's own entry goes with it on the
    partner book.
    """
    from .services_posting import unpost
    _safely(f"movement {instance.pk}", unpost, instance)


# ---------------------------------------------------------------------------
# Stock leaving the shelves
#
# Sender by name, so the accounting app does not import the warehouse at
# start-up; it is the warehouse that depends on accounting, not the other
# way round.
# ---------------------------------------------------------------------------
@receiver(post_save, sender="operating.StockMovement")
def post_stock_movement_to_ledger(sender, instance, raw=False, **kwargs):
    """Take the cost of goods sold out of stock as the goods leave."""
    if raw:
        return
    from .services_posting import post_stock_movement
    _safely(f"stock movement {instance.pk}", post_stock_movement, instance)


@receiver(post_delete, sender="operating.StockMovement")
def unpost_stock_movement_from_ledger(sender, instance, **kwargs):
    from .services_posting import unpost
    _safely(f"stock movement {instance.pk}", unpost, instance)


# ---------------------------------------------------------------------------
# The cash journal
# ---------------------------------------------------------------------------
def _cash_source_model(entry):
    """The lowercased model name behind this cash row, or None."""
    from django.contrib.contenttypes.models import ContentType

    if not entry.content_type_id:
        return None
    return ContentType.objects.get(pk=entry.content_type_id).model


@receiver(post_save, sender=CashTransactionEntry)
def post_cash_entry_to_ledger(sender, instance, raw=False, **kwargs):
    """Post the cash rows that carry their own contra, and only those.

    The filter is the same table the backfill reads, checked here rather
    than inside the posting call so that a transfer or a payment is passed
    over in silence instead of logging a warning on every save. Those two
    are not mistakes — they are events whose other leg is recorded
    elsewhere, and the absence is the point.
    """
    if raw:
        return
    from .services_posting import CASH_CONTRA_BY_SOURCE, post_cash_entry

    if _cash_source_model(instance) not in CASH_CONTRA_BY_SOURCE:
        return
    _safely(f"cash entry {instance.pk}", post_cash_entry, instance)


@receiver(post_delete, sender=CashTransactionEntry)
def unpost_cash_entry_from_ledger(sender, instance, **kwargs):
    """A cancelled dividend or expense takes its entry with it.

    Keyed on the ids the row still carries rather than on the object it
    names, because the usual way a cash row dies is a CASCADE from that
    very object — which is therefore already gone by the time this runs.
    """
    from .services_posting import CASH_CONTRA_BY_SOURCE, unpost_ref

    if _cash_source_model(instance) not in CASH_CONTRA_BY_SOURCE:
        return
    _safely(f"cash entry {instance.pk}", unpost_ref,
            instance.content_type_id, instance.content_pk)
