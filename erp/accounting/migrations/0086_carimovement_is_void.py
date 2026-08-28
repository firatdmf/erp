"""Give every ledger row a stored answer to "does this count?".

Balances and statements were two views of one ledger that decided
membership separately — recompute_balance summed every row, the
statement re-derived "is this half of a cancelled document's pair?" per
render — and agreed only while the excluded set happened to sum to zero.
A hard-deleted payment broke that: the CANCEL half was matched on its
reference text, which outlived the document, while the half it cancelled
was matched on the document's status, which did not. PERAKENDE's
statement closed at -150.00 against an account page reading 0.00.

This backfills the predicate the statement used to recompute, once, into
a column both callers now read.

Balances do not move. Every voided row is half of a pair summing to
zero, verified per account before this was written (44 rows across 865,
netting to 0.00 on every account), so excluding them from
recompute_balance leaves each cached_balance exactly where it was.
"""

from django.db import migrations, models
from django.db.models import Q


def _void_pairs(apps, schema_editor):
    """Flag both halves of every historical cancel pair.

    Deliberately a copy of the predicate rather than an import of it: the
    live one is about to be deleted, and a migration has to keep meaning
    what it meant on the day it ran.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    CariMovement = apps.get_model("accounting", "CariMovement")
    Payment = apps.get_model("accounting", "Payment")
    Invoice = apps.get_model("accounting", "Invoice")
    Check = apps.get_model("accounting", "CheckOrPromissoryNote")

    def ct(model, name):
        row = ContentType.objects.filter(
            app_label="accounting", model=name).first()
        return row.id if row else None

    pay_ct = ct(Payment, "payment")
    inv_ct = ct(Invoice, "invoice")
    chk_ct = ct(Check, "checkorpromissorynote")
    doc_cts = [c for c in (pay_ct, inv_ct, chk_ct) if c]
    if not doc_cts:
        return

    # (a) The CANCEL counter-rows, matched on their reference text.
    counter_q = (
        Q(movement_type="adjustment")
        & Q(source_type_id__in=doc_cts)
        & Q(source_id__isnull=False)
        & (Q(reference__startswith="CANCEL") | Q(description__startswith="CANCEL"))
    )

    # (b) The rows they cancel, matched on the document's status.
    cancelled = {
        pay_ct: set(Payment.objects.filter(status="cancelled")
                    .values_list("pk", flat=True)),
        inv_ct: set(Invoice.objects.filter(status="cancelled")
                    .values_list("pk", flat=True)),
        chk_ct: set(Check.objects.filter(status="cancelled")
                    .values_list("pk", flat=True)),
    }
    original_q = Q(pk__in=[])
    for ct_id, ids in cancelled.items():
        if ct_id and ids:
            original_q |= (Q(source_type_id=ct_id) & Q(source_id__in=list(ids)))
    original_q |= Q(payment__status="cancelled")
    original_q |= Q(invoice__status="cancelled")
    original_q |= Q(check_initial__status="cancelled")
    original_q |= Q(check_endorsement__status="cancelled")

    # (c) Both halves of a pair whose document was DELETED outright. This
    #     is the case the two clauses above disagreed on, and the reason
    #     the statement and the account page could drift apart at all.
    live = {
        pay_ct: set(Payment.objects.values_list("pk", flat=True)),
        inv_ct: set(Invoice.objects.values_list("pk", flat=True)),
        chk_ct: set(Check.objects.values_list("pk", flat=True)),
    }
    orphan_q = Q(pk__in=[])
    seen = set()
    for _pk, st, sid in CariMovement.objects.filter(counter_q).values_list(
            "pk", "source_type_id", "source_id"):
        if st in live and sid not in live[st] and (st, sid) not in seen:
            seen.add((st, sid))
            orphan_q |= (Q(source_type_id=st) & Q(source_id=sid))

    CariMovement.objects.filter(counter_q | original_q | orphan_q).update(is_void=True)


def _unvoid(apps, schema_editor):
    """Reverse: the column goes away with the field, so just clear it."""
    apps.get_model("accounting", "CariMovement").objects.update(is_void=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0085_caritransfer_exchange_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='carimovement',
            name='is_void',
            field=models.BooleanField(db_index=True, default=False, help_text="Excluded from balances and statements, but kept on the record — one half of a cancelled document's pair."),
        ),
        migrations.RunPython(_void_pairs, _unvoid),
    ]
