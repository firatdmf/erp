"""Record what caused a stock movement instead of describing it in text.

Shipping writes BOTH a consumed OrderRollReservation and a StockMovement(out)
for the same metres. Nothing linked them, so code reporting where a roll went
had to guess which pairs were one event — matched by amount, because the two
rows can land on different days. That guess mis-reports whenever a hand cut
happens to be the same length as a shipment on the same roll.

These FKs make the pairing a fact. The backfill applies the old guess ONCE,
to history, so existing rows get linked and the guess never runs again:

  * a consumed reservation claims the out-movement on its roll with the same
    metres, nearest in time — one movement per reservation, never shared;
  * remaining out-movements whose reference names an order ("Order #241",
    or an order_number) get `order` set, without a reservation.

Deliberately conservative: anything that doesn't match cleanly is left
unlinked and still reads from its reason text, which is what it did before.
"""
from django.db import migrations, models
import django.db.models.deletion
import re


def link_history(apps, schema_editor):
    StockMovement = apps.get_model("operating", "StockMovement")
    Reservation = apps.get_model("operating", "OrderRollReservation")
    Order = apps.get_model("operating", "Order")

    # ── 1. Pair consumed holds with the ledger row they produced ──
    outs = {}
    for mv in (StockMovement.objects
               .filter(movement_type="out", roll__isnull=False,
                       reservation__isnull=True)
               .only("id", "roll_id", "quantity", "created_at")):
        outs.setdefault((mv.roll_id, mv.quantity), []).append(mv)

    taken = set()
    linked_res = 0
    for res in (Reservation.objects
                .filter(consumed=True, roll__isnull=False)
                .only("id", "roll_id", "meters", "consumed_at", "order_id")):
        bucket = outs.get((res.roll_id, res.meters)) or []
        free = [m for m in bucket if m.id not in taken]
        if not free:
            continue
        # Nearest in time to the consumption, so several cuts of equal size
        # on one roll pair up in the order they happened rather than at random.
        if res.consumed_at:
            free.sort(key=lambda m: abs((m.created_at - res.consumed_at).total_seconds()))
        chosen = free[0]
        taken.add(chosen.id)
        StockMovement.objects.filter(pk=chosen.id).update(
            reservation_id=res.id, order_id=res.order_id)
        linked_res += 1

    # ── 2. Order cuts with no hold: read the order out of the reference ──
    numbers = {}
    for o in Order.objects.all().only("id"):
        numbers[f"Order #{o.id}"] = o.id
    for o in Order.objects.exclude(order_number__isnull=True).only("id", "order_number"):
        if (o.order_number or "").strip():
            numbers[o.order_number.strip()] = o.id

    linked_order = 0
    for mv in (StockMovement.objects
               .filter(movement_type="out", order__isnull=True)
               .exclude(reference__isnull=True)
               .only("id", "reference")):
        ref = (mv.reference or "").strip()
        oid = numbers.get(ref)
        if oid is None:
            m = re.match(r"^Order #(\d+)$", ref)
            oid = int(m.group(1)) if m and int(m.group(1)) in numbers.values() else None
        if oid is not None:
            StockMovement.objects.filter(pk=mv.id).update(order_id=oid)
            linked_order += 1

    print(f"    linked {linked_res} movements to their reservation, "
          f"{linked_order} more to an order by reference")


def unlink_history(apps, schema_editor):
    """Nothing to restore — the columns go away with the fields."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0069_realign_reservation_warehouse_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="order",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements",
                to="operating.order",
                help_text="The order this movement was made for, when applicable.",
            ),
        ),
        migrations.AddField(
            model_name="stockmovement",
            name="reservation",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements",
                to="operating.orderrollreservation",
                help_text="The packing-scan hold this cut realised, when applicable.",
            ),
        ),
        migrations.RunPython(link_history, unlink_history),
    ]
