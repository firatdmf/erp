from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def backfill_rates(apps, schema_editor):
    """Recover the rate each existing entry was converted at.

    Rows written before the rate was recorded still hold both halves of the
    sum — the amount and what it came to in base currency — so the rate is
    exactly what divides one into the other. Recovering it beats fetching a
    fresh one, which would be a different day's number and would not
    reproduce the figure sitting in the row.

    Entries already in their book's base currency are left null: nothing was
    converted, and a rate of 1 there would be a fact about nothing.
    """
    CashTransactionEntry = apps.get_model("accounting", "CashTransactionEntry")

    for entry in CashTransactionEntry.objects.select_related(
        "book", "book__base_currency", "currency"
    ).filter(exchange_rate__isnull=True):
        base = entry.book.base_currency
        if base is None or entry.currency_id == base_id(base):
            continue
        if not entry.amount or entry.amount_in_base_currency is None:
            continue
        rate = (
            Decimal(entry.amount_in_base_currency) / Decimal(entry.amount)
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        CashTransactionEntry.objects.filter(pk=entry.pk).update(exchange_rate=rate)


def base_id(currency):
    return currency.pk


def noop(apps, schema_editor):
    """Reversing leaves the recovered rates; they describe rows either way."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0081_payment_exchange_rate_nullable"),
    ]

    operations = [
        migrations.RunPython(backfill_rates, noop),
    ]
