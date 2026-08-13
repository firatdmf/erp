from django.db import migrations
from django.db.models import F


def realign_reservations(apps, schema_editor):
    """Point every live reservation at the warehouse its top is ACTUALLY in.

    Moving a top between warehouses (barcode read in another depot →
    "bu depoya taşı") only re-pointed WarehouseProductRoll.product; the
    denormalised OrderRollReservation.warehouse_product kept naming the
    source warehouse's product. The reserved metres therefore stayed
    displayed in the warehouse the top had left, never showed up in the one
    it arrived at, and would have been cut out of the source warehouse's
    quantity at ship time. The same-SKU dupe merge drifted the same way.

    Only unconsumed rows are realigned — a consumed reservation records
    where the stock physically went out from, which is history.
    """
    OrderRollReservation = apps.get_model("operating", "OrderRollReservation")

    stale = (OrderRollReservation.objects
             .filter(consumed=False, roll__isnull=False)
             .exclude(warehouse_product_id=F("roll__product_id"))
             .values_list("id", "roll__product_id"))

    rows = [OrderRollReservation(id=pk, warehouse_product_id=wp_id)
            for pk, wp_id in stale if wp_id is not None]

    for i in range(0, len(rows), 500):
        OrderRollReservation.objects.bulk_update(
            rows[i:i + 500], ["warehouse_product"])


def unrealign(apps, schema_editor):
    """No-op: the pre-fix pointer named a warehouse the top is no longer in,
    so there is nothing worth restoring."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0068_alter_order_cari_and_more"),
    ]

    operations = [
        migrations.RunPython(realign_reservations, unrealign),
    ]
