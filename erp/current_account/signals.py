"""
Signals for current_account.

Two responsibilities:

1. Auto-assign CARI-XXX code when a CariAccount is being created without one.
2. Mirror CariMovement → legacy accounting.AssetAccountsReceivable /
   LiabilityAccountsPayable so existing accounting dashboards & reports keep
   working without modification.

The mirror is one-way (Cari → legacy). Once we deprecate the legacy AR/AP
views we can remove this. For now both worlds coexist safely.
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
# 2. Mirror to legacy accounting AR/AP
# ---------------------------------------------------------------------------
def _mirror_to_legacy(movement):
    """
    Mirror a CariMovement into AssetAccountsReceivable (if amount > 0)
    or LiabilityAccountsPayable (if amount < 0).

    Skipped silently if neither side applies (zero amount, adjustment etc).
    """
    from accounting.models import AssetAccountsReceivable, LiabilityAccountsPayable

    cari = movement.cari

    if movement.amount > 0:
        # Cari owes us → Accounts Receivable
        ar_kwargs = dict(
            book=movement.book,
            currency=movement.currency,
            amount=movement.amount,
            paid=False,
        )
        # AR accepts contact/company/supplier — pick whichever cari has
        if cari.contact_id:
            ar_kwargs["contact"] = cari.contact
        elif cari.company_id:
            ar_kwargs["company"] = cari.company
        elif cari.supplier_id:
            ar_kwargs["supplier"] = cari.supplier

        if movement.legacy_ar_id:
            AssetAccountsReceivable.objects.filter(pk=movement.legacy_ar_id).update(
                **{k: v for k, v in ar_kwargs.items() if k != "paid"}
            )
        else:
            ar = AssetAccountsReceivable.objects.create(**ar_kwargs)
            CariMovement.objects.filter(pk=movement.pk).update(legacy_ar_id=ar.pk)

    elif movement.amount < 0:
        # We owe cari → Accounts Payable (supplier-only in legacy schema)
        if not cari.supplier_id:
            return  # legacy AP requires a supplier; skip if not applicable
        ap_kwargs = dict(
            book=movement.book,
            currency=movement.currency,
            amount=abs(movement.amount),
            supplier=cari.supplier,
            paid=False,
        )
        if movement.legacy_ap_id:
            LiabilityAccountsPayable.objects.filter(pk=movement.legacy_ap_id).update(
                **{k: v for k, v in ap_kwargs.items() if k != "paid"}
            )
        else:
            ap = LiabilityAccountsPayable.objects.create(**ap_kwargs)
            CariMovement.objects.filter(pk=movement.pk).update(legacy_ap_id=ap.pk)


@receiver(post_save, sender=CariMovement)
def mirror_movement_to_legacy(sender, instance, created, **kwargs):
    # Avoid mirroring during the backfill migration — it sets movement_type
    # to legacy_ar / legacy_ap and we don't want to write duplicates back.
    if instance.movement_type in ("legacy_ar", "legacy_ap"):
        return
    try:
        _mirror_to_legacy(instance)
    except Exception as exc:
        # Never block the save if the legacy mirror fails — log and continue.
        import logging
        logging.getLogger("current_account").warning(
            "Legacy mirror failed for CariMovement %s: %s", instance.pk, exc
        )


# ---------------------------------------------------------------------------
# 3. Mirror collection/payment CariMovements into Payment rows
#
# Without this, anything that creates a "collection" or "payment" type
# CariMovement directly (Add Movement form, manual code, scripts, etc.)
# would be invisible on the /cari/tahsilat/ list, which reads from
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
        logging.getLogger("current_account").warning(
            "Mirror to Payment failed for CariMovement %s: %s", instance.pk, exc,
        )


@receiver(post_delete, sender=CariMovement)
def unmirror_movement(sender, instance, **kwargs):
    from accounting.models import AssetAccountsReceivable, LiabilityAccountsPayable
    if instance.legacy_ar_id:
        AssetAccountsReceivable.objects.filter(pk=instance.legacy_ar_id).delete()
    if instance.legacy_ap_id:
        LiabilityAccountsPayable.objects.filter(pk=instance.legacy_ap_id).delete()
    # Refresh cached balance on the parent cari (movement is gone now)
    if instance.cari_id:
        try:
            instance.cari.recompute_balance(save=True)
        except CariAccount.DoesNotExist:
            pass
