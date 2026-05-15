"""
Data migration: backfill CariAccount + CariMovement from existing
accounting.AssetAccountsReceivable and LiabilityAccountsPayable rows.

Rules:
    * One CariAccount per (book, real-world entity).
    * If an entity has BOTH receivables and payables, the cari is marked type="both".
    * Every legacy AR row becomes a CariMovement(movement_type="legacy_ar",
      amount=+ar.amount, legacy_ar_id=ar.pk).
    * Every legacy AP row becomes a CariMovement(movement_type="legacy_ap",
      amount=-ap.amount, legacy_ap_id=ap.pk).
    * Cari code is auto-generated per book: CARI-001, CARI-002, ...
    * Idempotent: re-running skips rows whose legacy_*_id is already mirrored.

No legacy row is modified or deleted — both worlds coexist after backfill.
"""
from decimal import Decimal

from django.db import migrations


def _entity_key(row):
    if getattr(row, "contact_id", None):
        return ("contact", row.contact_id)
    if getattr(row, "company_id", None):
        return ("company", row.company_id)
    if getattr(row, "supplier_id", None):
        return ("supplier", row.supplier_id)
    return None


def _entity_name(kind, obj):
    if kind == "contact":
        return obj.name or f"Contact #{obj.pk}"
    if kind == "company":
        return obj.name or f"Company #{obj.pk}"
    if kind == "supplier":
        return obj.company_name or obj.contact_name or f"Supplier #{obj.pk}"
    return "Bilinmeyen"


def backfill(apps, schema_editor):
    CariAccount  = apps.get_model("current_account", "CariAccount")
    CariMovement = apps.get_model("current_account", "CariMovement")
    CariSettings = apps.get_model("current_account", "CariSettings")

    AR       = apps.get_model("accounting", "AssetAccountsReceivable")
    AP       = apps.get_model("accounting", "LiabilityAccountsPayable")
    Currency = apps.get_model("accounting", "CurrencyCategory")
    Contact  = apps.get_model("crm", "Contact")
    Company  = apps.get_model("crm", "Company")
    Supplier = apps.get_model("crm", "Supplier")

    def get_settings(book):
        obj, _ = CariSettings.objects.get_or_create(book=book)
        return obj

    def make_code(settings_obj):
        code = f"{settings_obj.cari_code_prefix}-{str(settings_obj.next_cari_seq).zfill(settings_obj.cari_code_padding)}"
        settings_obj.next_cari_seq += 1
        settings_obj.save(update_fields=["next_cari_seq"])
        return code

    entity_model = {"contact": Contact, "company": Company, "supplier": Supplier}

    def find_or_create_cari(book, kind, entity_id):
        lookup = {f"{kind}_id": entity_id, "book": book}
        existing = CariAccount.objects.filter(**lookup).first()
        if existing:
            return existing

        entity = entity_model[kind].objects.filter(pk=entity_id).first()
        if not entity:
            return None  # legacy row references a deleted entity; skip

        usd = Currency.objects.filter(code="USD").first() or Currency.objects.first()
        type_default = {"contact": "customer", "company": "customer", "supplier": "supplier"}[kind]

        return CariAccount.objects.create(
            book=book,
            code=make_code(get_settings(book)),
            name=_entity_name(kind, entity)[:200],
            type=type_default,
            default_currency=usd,
            **{f"{kind}_id": entity_id},
        )

    def upgrade_to_both(cari, new_kind):
        if cari.type in ("customer", "supplier") and cari.type != new_kind:
            cari.type = "both"
            cari.save(update_fields=["type"])

    # ----- AR backfill -----------------------------------------------------
    for ar in AR.objects.all().select_related("book", "currency",
                                              "contact", "company", "supplier"):
        key = _entity_key(ar)
        if not key:
            continue
        kind, entity_id = key
        cari = find_or_create_cari(ar.book, kind, entity_id)
        if not cari:
            continue
        if CariMovement.objects.filter(legacy_ar_id=ar.pk).exists():
            continue

        CariMovement.objects.create(
            cari=cari,
            book=ar.book,
            date=ar.created_at.date() if hasattr(ar.created_at, "date") else ar.created_at,
            amount=ar.amount,
            currency=ar.currency,
            exchange_rate=Decimal("1.000000"),
            amount_base=ar.amount,
            movement_type="legacy_ar",
            description="Eski sistem alacak kaydı (otomatik aktarıldı)",
            legacy_ar_id=ar.pk,
        )
        upgrade_to_both(cari, "customer")

    # ----- AP backfill -----------------------------------------------------
    for ap in AP.objects.all().select_related("book", "currency", "supplier"):
        key = _entity_key(ap)
        if not key:
            continue
        kind, entity_id = key
        cari = find_or_create_cari(ap.book, kind, entity_id)
        if not cari:
            continue
        if CariMovement.objects.filter(legacy_ap_id=ap.pk).exists():
            continue

        CariMovement.objects.create(
            cari=cari,
            book=ap.book,
            date=ap.created_at.date() if hasattr(ap.created_at, "date") else ap.created_at,
            amount=-ap.amount,
            currency=ap.currency,
            exchange_rate=Decimal("1.000000"),
            amount_base=-ap.amount,
            movement_type="legacy_ap",
            description="Eski sistem borç kaydı (otomatik aktarıldı)",
            legacy_ap_id=ap.pk,
        )
        upgrade_to_both(cari, "supplier")

    # ----- Refresh cached balances ----------------------------------------
    from django.db.models import Sum, Max
    for cari in CariAccount.objects.all():
        agg = cari.movements.aggregate(
            total=Sum("amount"),
            total_base=Sum("amount_base"),
            last=Max("created_at"),
        )
        CariAccount.objects.filter(pk=cari.pk).update(
            cached_balance=(agg["total"] or Decimal("0.00")),
            cached_balance_base=(agg["total_base"] or Decimal("0.00")),
            last_movement_at=agg["last"],
        )


def unbackfill(apps, schema_editor):
    """
    Remove every CariMovement that was created from legacy AR/AP,
    plus any CariAccounts that have no remaining movements.
    Legacy AR/AP rows themselves are NOT touched.
    """
    CariMovement = apps.get_model("current_account", "CariMovement")
    CariAccount  = apps.get_model("current_account", "CariAccount")

    CariMovement.objects.filter(movement_type__in=["legacy_ar", "legacy_ap"]).delete()
    CariAccount.objects.filter(movements__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("current_account", "0001_initial"),
        ("accounting", "0065_alter_liabilityaccountspayable_supplier"),
        ("crm", "0017_convert_contact_email_phone_to_arrays"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=unbackfill),
    ]
