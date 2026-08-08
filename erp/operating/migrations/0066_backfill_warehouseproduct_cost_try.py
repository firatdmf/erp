from decimal import Decimal

from django.db import migrations


def backfill_cost_try(apps, schema_editor):
    """Fill the empty cost_try column so TRY figures stop depending on
    today's FX rate.

    Only 43 of ~1,200 products ever had cost_try stored, so almost every
    lira number in the UI was coming from unit_cost_try()'s live-rate
    fallback — meaning a product's "historical cost" silently moved every
    time the rate did. This freezes it, using the USD/TRY rate that was
    current WHEN THE PRODUCT WAS CREATED (latest rate on or before that
    date), not the rate today.

    Skips anything already populated, and anything we cannot derive a
    figure for (no cost_usd and not a TRY purchase) — those keep falling
    back at read time exactly as before.
    """
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    CurrencyExchangeRate = apps.get_model("accounting", "CurrencyExchangeRate")

    # Whole rate history in one query — one dict lookup per product beats
    # a query per row against a remote DB.
    rates = list(
        CurrencyExchangeRate.objects
        .filter(from_currency__iexact="USD", to_currency__iexact="TRY")
        .order_by("date")
        .values_list("date", "rate")
    )
    if not rates:
        return  # fresh/empty environment — nothing to freeze against

    def rate_on(day):
        """Latest rate on or before `day`; the oldest rate if the product
        predates the series (better than leaving the row unfrozen)."""
        chosen = rates[0][1]
        for d, r in rates:
            if d <= day:
                chosen = r
            else:
                break
        return chosen

    pending = (WarehouseProduct.objects
               .filter(cost_try__isnull=True)
               .only("id", "cost_usd", "purchase_price", "purchase_currency",
                     "created_at", "cost_try"))

    updates = []
    for wp in pending.iterator(chunk_size=500):
        currency = (wp.purchase_currency or "USD").upper()
        if currency == "TRY" and wp.purchase_price is not None:
            # Bought in lira — the purchase price IS the lira cost.
            wp.cost_try = Decimal(wp.purchase_price).quantize(Decimal("0.0001"))
        elif wp.cost_usd is not None:
            day = wp.created_at.date() if wp.created_at else rates[-1][0]
            wp.cost_try = (Decimal(wp.cost_usd) * Decimal(rate_on(day))).quantize(
                Decimal("0.0001"))
        else:
            continue
        updates.append(wp)

    for i in range(0, len(updates), 500):
        WarehouseProduct.objects.bulk_update(updates[i:i + 500], ["cost_try"])


def unbackfill(apps, schema_editor):
    """Deliberately a no-op: we cannot tell a backfilled cost_try from one
    that was always there, and blanking real costs would be worse than
    leaving the frozen figures in place."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0065_alter_warehouseproduct_cost_try_and_more"),
        ("accounting", "0065_alter_liabilityaccountspayable_supplier"),
    ]

    operations = [
        migrations.RunPython(backfill_cost_try, unbackfill),
    ]
