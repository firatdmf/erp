"""Put a warehouse's stock on the books when the cutover photograph missed it.

`backfill_ledger` posts one `Opening inventory` entry per book, valuing
whatever stood in that book's warehouses on the day it ran. A warehouse
opened AFTER that day is invisible to it: the shelves fill up, the balance
sheet's subsidiary column counts them because it reads the warehouse
directly, and account 1300 goes on holding the older photograph. Nothing
posts the difference later — the COGS wiring added in f9b4ea95 relieves
stock as goods leave, but nothing books stock that arrived without a
purchase invoice behind it.

That is the whole of Ergene's remaining gap. Its cutover was 2026-09-03 and
photographed 376,906.10 in Ergene Fabrika, which is still exactly what 1300
says. On 2026-09-08 a second warehouse, Ready-made Shop, was loaded by the
READYMADE-STOCK-IMPORT batch: 45 movements, 214 items, 2,796.00 metres,
worth 50,168.45. No purchase invoice, no current account movement, no
journal entry — and 50,168.45 is, to the cent, the amount by which the
warehouse exceeds the ledger.

So this is not a plug. It is the same entry backfill_ledger would have
written had the shelves existed when it ran, posted for one warehouse:

    Dr 1300 Inventory                   50,168.45
        Cr 3100 Opening Balance Equity  50,168.45

Equity is the right contra for the same reason it is right in the book-wide
entry — this stock came in with the business rather than being bought by
it, and there is no payable left standing against it. If these goods ARE
still owed for, pass --contra 2000 and the credit becomes a payable
instead; that is a question about these particular curtains, not about the
accounting, and only somebody who knows where they came from can answer it.

Refuses to post anything that would put 1300 ABOVE the stock actually on
the shelves, which is the one way this could do damage: run it on a
warehouse the cutover already covered and the book-wide entry plus this one
would count the same rolls twice. Idempotent — an entry naming the
warehouse means it is already done.

Dry run by default; pass --apply to commit.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min

from accounting.models import Book
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import _inventory_value, ensure_chart
from accounting.services_posting import post_opening_inventory


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Post one warehouse's opening stock into the ledger."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int, required=True,
                            help="Book id the warehouse belongs to.")
        parser.add_argument("--warehouse", type=int, required=True,
                            help="Warehouse id whose stock is missing from 1300.")
        parser.add_argument("--date", default=None,
                            help="Entry date (default: the warehouse's first "
                                 "stock movement — the day the shelves filled).")
        parser.add_argument("--contra", default="3100",
                            help="Credit account. 3100 Opening Balance Equity "
                                 "by default; 2000 if the stock is still owed for.")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        from operating.models import StockMovement, Warehouse

        w = self.stdout.write
        ensure_chart()

        try:
            book = Book.objects.get(pk=opts["book"])
        except Book.DoesNotExist:
            raise CommandError(f"No book with id {opts['book']}.")
        try:
            warehouse = Warehouse.objects.get(pk=opts["warehouse"])
        except Warehouse.DoesNotExist:
            raise CommandError(f"No warehouse with id {opts['warehouse']}.")
        if warehouse.accounting_book_id != book.pk:
            raise CommandError(
                f"Warehouse {warehouse.pk} ({warehouse.name}) belongs to book "
                f"{warehouse.accounting_book_id}, not {book.pk}. Stock belongs "
                f"to whoever owns the shelves — post it to that book.")

        description = f"Opening inventory — {warehouse.name}"
        if JournalEntry.objects.filter(book=book,
                                       description=description).exists():
            w(self.style.NOTICE(
                f"{warehouse.name} already has an opening inventory entry — "
                f"nothing to do."))
            return

        date = opts["date"]
        if date is None:
            date = (StockMovement.objects
                    .filter(product__warehouse=warehouse)
                    .aggregate(d=Min("created_at"))["d"])
            if date is None:
                raise CommandError(
                    f"{warehouse.name} has no stock movements, so there is no "
                    f"date to post on. Pass --date.")
            date = date.date()

        value, unvalued_n, unvalued_qty = _inventory_value(book, warehouse)
        if value <= Decimal("0.00"):
            w(self.style.NOTICE(
                f"{warehouse.name} holds nothing valued — nothing to post."))
            return

        # The one way this could do harm: posting shelves the book-wide
        # cutover entry already counted. Compare against the whole book, not
        # this warehouse, because that is the figure 1300 is reconciled to.
        shelves, _n, _q = _inventory_value(book)
        ledger = _ledger_inventory(book)
        if ledger + value > shelves:
            raise CommandError(
                f"Refusing: 1300 holds {ledger} and the book's shelves hold "
                f"{shelves}. Posting {value} would put the ledger "
                f"{ledger + value - shelves} ABOVE the stock that exists, "
                f"which means the cutover entry already covers "
                f"{warehouse.name}.")

        w(f"Book {book.pk}: {book.name}")
        w(f"  warehouse {warehouse.pk}: {warehouse.name}")
        w(f"  date      {date}")
        w(f"  ledger 1300 now {ledger}   book's shelves {shelves}   "
          f"gap {shelves - ledger}")
        w("")
        w(f"    Dr 1300 Inventory                {value:>14}")
        w(f"        Cr {opts['contra']} {_name(opts['contra']):<26}{value:>14}")
        if unvalued_n:
            w(self.style.WARNING(
                f"\n  {unvalued_n} item(s) ({unvalued_qty}) in this warehouse "
                f"carry no cost and are outside that figure — they are outside "
                f"the balance sheet's figure too, so this does not create a "
                f"difference, it leaves one."))

        try:
            with transaction.atomic():
                entry, _n, _q = post_opening_inventory(
                    book, date=date, warehouse=warehouse,
                    contra=opts["contra"],
                    reference=f"LEDGER-OB-WH{warehouse.pk}")
                after = _ledger_inventory(book)
                w(f"\n  entry {entry.pk}: {entry.description!r}")
                w(f"  1300 now {after}   shelves {shelves}   "
                  f"gap {shelves - after}")
                if after == shelves:
                    w(self.style.SUCCESS("  inventory reconciles"))
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. "
                                "Re-run with --apply."))
            return
        w(self.style.SUCCESS(
            f"\nCommitted. Undo with reference='LEDGER-OB-WH{warehouse.pk}'."))


def _ledger_inventory(book):
    """What account 1300 says this book holds."""
    from django.db.models import Sum
    from accounting.models_ledger import JournalLine

    rows = JournalLine.objects.filter(entry__book=book, account__code="1300")
    d = rows.aggregate(t=Sum("debit"))["t"] or Decimal("0.00")
    c = rows.aggregate(t=Sum("credit"))["t"] or Decimal("0.00")
    return d - c


def _name(code):
    from accounting.models_ledger import ChartAccount
    row = ChartAccount.objects.filter(code=code).first()
    return row.name if row else "?"
