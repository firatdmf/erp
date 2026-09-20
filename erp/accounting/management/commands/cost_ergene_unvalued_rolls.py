"""Put a cost on the five Ergene rolls that carry none, and book it.

`_inventory_value` counts an item at its own stamp, then the purchase line
it arrived on, then the product's current cost. Five rolls in Ergene
Fabrika have none of the three — each is the only item on its product, and
that product's cost_usd is null — so 95.42 metres of real fabric is counted
in the unvalued column and valued at nothing:

    23066  K12566.T26    2000045488403  20.10m  MAMUL DEPO · 2. kalite
    23212  K12741.G157   2000043306709  15.00m  MAMUL DEPO · 2. kalite
    25330  K24802.G76    2000041165704  19.80m  MAMUL DEPO · 2. kalite
    25332  K24812.G93    2000041165605  20.52m  MAMUL DEPO · 2. kalite
    26717  N1378.???     X0000002       20.00m  barkodsuz geldi; X0000002 basıldı

They reconcile today only because BOTH sides exclude them identically. The
cost of leaving them is not the balance sheet, it is the next sale:
lines_for_stock_movement returns no lines when stock_unit_cost is None, so
one of these shipping books revenue with no cost against it and reads as
100% margin.

Stamping unit_cost_base is what fixes that — it is the figure both the
balance sheet and the COGS path read first, and the only one of the three
that cannot move under you later (cost_usd is a last-purchase price the
intake path rewrites on every batch).

THE ENTRY IS NOT OPTIONAL. Stamping a cost RAISES what the warehouse is
worth, so doing it alone would push the shelves 95.42 above account 1300
and reopen an inventory difference that is otherwise closed. Both halves
belong to one event and this does them together, or neither:

    Dr 1300 Inventory                   95.42
        Cr 3100 Opening Balance Equity  95.42

Equity for the same reason as the rest of the opening stock — this fabric
was always on the shelf, nobody bought it just now; all that changed is
that somebody finally said what it was worth.

$1.00/metre is a decision about these five rolls, not a rule about seconds.
Pass --rate to say otherwise.

Idempotent: an item that already carries a stamp is left alone, and the
entry is written once. Dry run by default; pass --apply to commit.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Book
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import ensure_chart
from accounting.services_posting import credit, debit, post_entry

BOOK_PK = 5
# Barcode alongside the id so a mistyped pk cannot silently cost the wrong
# roll: the pair has to agree or nothing is written.
ROLLS = {
    23066: "2000045488403",
    23212: "2000043306709",
    25330: "2000041165704",
    25332: "2000041165605",
    26717: "X0000002",
}
DESCRIPTION = "Value previously uncosted stock"
REFERENCE = "ERG-UNVALUED-2026"


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Stamp a cost on Ergene's five uncosted rolls and post the value."

    def add_arguments(self, parser):
        parser.add_argument("--rate", default="1.00",
                            help="Cost per metre (default 1.00).")
        parser.add_argument("--date", default="2026-09-21",
                            help="Entry date (default today's cutover).")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        from operating.models import WarehouseProductItem

        w = self.stdout.write
        ensure_chart()
        rate = Decimal(opts["rate"])
        if rate <= 0:
            raise CommandError("--rate must be positive.")

        book = Book.objects.get(pk=BOOK_PK)
        if JournalEntry.objects.filter(book=book,
                                       description=DESCRIPTION).exists():
            w(self.style.NOTICE("Already valued — nothing to do."))
            return

        items = (WarehouseProductItem.objects
                 .filter(pk__in=ROLLS)
                 .select_related("product", "product__warehouse"))
        found = {i.pk: i for i in items}
        missing = set(ROLLS) - set(found)
        if missing:
            raise CommandError(f"Items not found: {sorted(missing)}.")
        for pk, item in found.items():
            if item.barcode != ROLLS[pk]:
                raise CommandError(
                    f"Item {pk} has barcode {item.barcode!r}, expected "
                    f"{ROLLS[pk]!r}. Refusing to cost a roll that is not the "
                    f"one this command was written for.")
            if item.product.warehouse.accounting_book_id != book.pk:
                raise CommandError(
                    f"Item {pk} sits in {item.product.warehouse.name}, which "
                    f"is not {book.name}'s.")

        total = Decimal("0.00")
        w(f"{book.name} — costing at {rate}/metre\n")
        stamped = []
        for pk in sorted(found):
            item = found[pk]
            if item.unit_cost_base is not None:
                w(f"  {pk:>6}  already stamped {item.unit_cost_base} — left alone")
                continue
            qty = Decimal(item.quantity_remaining)
            value = (qty * rate).quantize(Decimal("0.01"))
            total += value
            stamped.append(item)
            w(f"  {pk:>6}  {item.product.sku or '':<14} {qty:>7}m x {rate} "
              f"= {value:>8}   {item.product.name[:40]}")

        if not stamped:
            w(self.style.NOTICE("\nEvery roll already carries a cost."))
            return

        w(f"\n    Dr 1300 Inventory                {total:>10}")
        w(f"        Cr 3100 Opening Balance Equity{total:>10}")

        try:
            with transaction.atomic():
                for item in stamped:
                    item.unit_cost_base = rate
                    item.save(update_fields=["unit_cost_base"])
                entry = post_entry(
                    book=book, date=opts["date"], description=DESCRIPTION,
                    lines=[debit("1300", total, memo="Stock valued at last"),
                           credit("3100", total, memo="Stock valued at last")],
                    reference=REFERENCE,
                )
                w(f"\n  entry {entry.pk}")
                self._report(book, w)
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. "
                                "Re-run with --apply."))
            return
        w(self.style.SUCCESS(
            f"\nCommitted. Undo the entry with reference={REFERENCE!r} — the "
            f"stamps themselves have to be cleared by hand."))

    def _report(self, book, w):
        from accounting.services_ledger import reconcile

        rec = reconcile(book)
        w("")
        for row in rec["rows"]:
            mark = "ok" if row["reconciled"] else "OFF"
            w(f"  {row['label']:<28} ledger={row['ledger']:>13} "
              f"subsidiary={row['subsidiary']:>13}  {mark}")
