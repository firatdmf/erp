"""
Signals for the accounting cari ledger.

Two responsibilities:

1. Auto-assign CARI-XXX code when a CariAccount is being created without one.
2. Mirror collection/payment CariMovements into Payment rows, so a movement
   entered anywhere still appears on the payments list.

There used to be a third: a one-way mirror of every movement into the old
AssetAccountsReceivable / LiabilityAccountsPayable tables, kept so the
legacy accounting dashboards would go on working. Those tables are gone.
They were append-only and lossy — a payable was skipped outright unless
the account happened to carry a supplier FK, and gross rows were never
netted — which is why the accounting equation stopped reading them long
before this. Receivables and payables are CariAccount.cached_balance now,
and that is the only place they are.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .models import CariAccount, CariMovement, CariSettings


# ---------------------------------------------------------------------------
# 1. Auto-generate CARI-XXX code
# ---------------------------------------------------------------------------
@receiver(pre_save, sender=CariAccount)
def assign_cari_code(sender, instance, **kwargs):
    if instance.code:
        return
    if not instance.book_id:
        return
    settings_obj = CariSettings.for_book(instance.book)
    instance.code = settings_obj.next_cari_code()


# ---------------------------------------------------------------------------
# 1b. Suppliers deliberately DON'T auto-create a cari any more.
#
#     This used to fire on every Supplier post_save, which is how the
#     account list filled up with duplicates: the balances staff maintain
#     were imported from KARVEN as plain caris with no Supplier link, so
#     adding a supplier named after one of them minted a SECOND, empty
#     account (MARKISS #210 next to MARKİSS TEKSTİL #163) — and warehouse
#     intake, which resolved through the supplier FK, then posted alım
#     invoices to the empty one while the real balance sat untouched.
#
#     Purchases now post to a cari picked directly in the intake panel
#     (see operating.views_warehouse.WarehouseManualAdd), so nothing needs
#     a supplier→cari bridge. Suppliers remain a CRM/procurement concept.
#     Accounts are created explicitly: the accounting UI, or the intake
#     panel's inline "new account" box (warehouse_account_create).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Mirror collection/payment CariMovements into Payment rows
#
# Without this, anything that creates a "collection" or "payment" type
# CariMovement directly (Add Movement form, manual code, scripts, etc.)
# would be invisible on the /accounting/accounts/payments/ list, which reads from
# Payment — not from CariMovement. We post_save here so EVERY entry
# point gets covered, not just the one explicit view.
# ---------------------------------------------------------------------------
@receiver(post_save, sender=CariMovement)
def mirror_movement_to_payment(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.movement_type not in ("collection", "payment"):
        return
    # Already linked from a Payment.confirm() call — that path created
    # the Payment first and then the movement, so we don't want to
    # double-up here.
    #
    # IMPORTANT: the OneToOne back-reference (`instance.payment`) is NOT
    # set yet at this point — confirm() creates the movement first and
    # only assigns posted_movement afterwards. So hasattr() alone races
    # and creates a duplicate Payment, which then fails the unique
    # constraint on posted_movement_id.
    #
    # The reliable signal is source_type/source_id: confirm() sets both
    # to the Payment that owns this movement. If either is present, skip.
    if hasattr(instance, "payment"):
        return
    try:
        from .models import Payment
        if (
            instance.source_type_id
            and instance.source_type.model_class() is Payment
            and instance.source_id
        ):
            return
    except Exception:
        # Defensive — if source_type lookup blows up, fall through to
        # mirror behaviour rather than crashing the save.
        pass
    # Skip during legacy backfills.
    if instance.movement_type in ("legacy_ar", "legacy_ap"):
        return

    try:
        from .views_payment import _next_payment_number
        from .models import Payment
        Payment.objects.create(
            cari=instance.cari,
            book=instance.book,
            number=_next_payment_number(instance.book, instance.movement_type),
            type=instance.movement_type,
            method="cash",
            status="confirmed",
            date=instance.date,
            amount=abs(instance.amount),
            currency=instance.currency,
            description=instance.description,
            notes=instance.reference,
            posted_movement=instance,
            created_by=instance.created_by,
        )
    except Exception as exc:
        import logging
        logging.getLogger("accounting.accounts").warning(
            "Mirror to Payment failed for CariMovement %s: %s", instance.pk, exc,
        )


@receiver(post_delete, sender=CariMovement)
def recompute_after_delete(sender, instance, **kwargs):
    """A deleted movement leaves a balance that no longer counts it.

    This used to also delete the legacy AR/AP rows the movement mirrored
    into; those tables are gone, so recomputing is all that is left — and
    it is the part that always mattered, since cached_balance is what the
    account page and the accounting equation both read.
    """
    # Refresh cached balance on the parent cari (movement is gone now)
    if instance.cari_id:
        try:
            instance.cari.recompute_balance(save=True)
        except CariAccount.DoesNotExist:
            pass
