"""Delete the 0.00 ledger rows order-attached invoices used to post.

Invoice.issue() wrote a movement for every invoice, at the invoice total
when it stood alone and at 0.00 when it was raised against an order —
the order_sale already carried the receivable, so posting the total
again would have double-counted.

That left rows on the statement which could never explain how the
balance got from the line above them to the line below, which is the
only job a statement row has. On the retail account eleven of thirty-one
rows were such markers. Invoices are listed on the account page in their
own card; "was this invoiced?" is answered there.

issue() no longer writes them. This removes the ones already written.

Balances do not move: every row deleted here is 0.00 by construction —
asserted below rather than assumed. `last_movement_at` can shift on an
account whose newest row was a marker, so the affected accounts are
recomputed.

STANDALONE invoices are untouched. For a purchase receipt or a sale with
no order behind it, that movement IS the debt and nothing else creates
it.
"""

from django.db import migrations
from django.db.models import Max, Sum


def _drop_markers(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    CariMovement = apps.get_model("accounting", "CariMovement")
    CariAccount = apps.get_model("accounting", "CariAccount")
    Invoice = apps.get_model("accounting", "Invoice")

    inv_ct = ContentType.objects.filter(
        app_label="accounting", model="invoice").first()
    if not inv_ct:
        return

    order_attached = set(
        Invoice.objects.exclude(order=None).values_list("pk", flat=True))
    if not order_attached:
        return

    markers = CariMovement.objects.filter(
        source_type_id=inv_ct.id, source_id__in=list(order_attached))

    # Refuse to touch anything carrying a value. If a row here is not
    # 0.00 then the assumption this migration rests on is wrong, and
    # deleting it would move a balance.
    nonzero = markers.exclude(amount=0).count()
    if nonzero:
        raise RuntimeError(
            f"{nonzero} order-attached invoice movements carry a non-zero "
            f"amount; refusing to delete them."
        )

    affected = list(markers.values_list("cari_id", flat=True).distinct())
    markers.delete()

    # Signals do not fire for historical models, so the cache is brought
    # back in step by hand. Only last_movement_at can actually differ.
    for cari_id in affected:
        agg = CariMovement.objects.filter(cari_id=cari_id, is_void=False).aggregate(
            total=Sum("amount_base"), last=Max("created_at"))
        CariAccount.objects.filter(pk=cari_id).update(
            cached_balance=agg["total"] or 0,
            last_movement_at=agg["last"],
        )


def _noop(apps, schema_editor):
    """Irreversible by design — the rows carried no information beyond
    'a document exists', which the invoice itself still records."""


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0087_drop_cached_balance_base'),
    ]

    operations = [
        migrations.RunPython(_drop_markers, _noop),
    ]
