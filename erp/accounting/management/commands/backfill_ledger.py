"""Replay a book's subsidiary ledgers into the general ledger.

The general ledger balances by construction — post_entry refuses an
unbalanced entry — but it starts empty, so until history is replayed it
reports a tidy zero while the money sits somewhere else entirely. This
puts what already happened into it:

  * every current account movement, against the contra its type implies
  * the stock standing in the book's warehouses, at what it cost
  * one entry moving credit-balance accounts from receivable to payable

Every entry is stamped with a batch reference so a run can be undone:

    JournalEntry.objects.filter(reference="LEDGER-BF-5").delete()

Idempotent: a movement that already has an entry is skipped, so a run
that stopped halfway can simply be run again.

Dry run by default; pass --apply to commit.
"""
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Book
from accounting.models_accounts import CurrentAccountMovement
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import (balance_sheet, ensure_chart,
                                        subsidiary_equation)
from accounting.services_posting import (CASH_CONTRA_BY_SOURCE, NoRuleFor,
                                         post_movement,
                                         post_opening_inventory,
                                         reclassify_payables)


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Post a book's existing cari movements and stock into the ledger."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int, required=True,
                            help="Book id to backfill.")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")
        parser.add_argument("--cutover", default=None,
                            help="Date for the inventory and reclass entries "
                                 "(default: the last movement's date).")

    def handle(self, *args, **opts):
        try:
            book = Book.objects.get(pk=opts["book"])
        except Book.DoesNotExist:
            raise CommandError(f"No book with id {opts['book']}.")

        w = self.stdout.write
        ref = f"LEDGER-BF-{book.pk}"
        ensure_chart()

        movements = list(CurrentAccountMovement.objects.filter(book=book)
                         .select_related("current_account", "currency").order_by("date", "id"))
        if not movements:
            raise CommandError(f"{book.name} has no cari movements.")
        cutover = opts["cutover"] or max(m.date for m in movements)

        # Movements already posted, so a half-finished run can be resumed.
        ct = ContentType.objects.get_for_model(CurrentAccountMovement)
        done = set(JournalEntry.objects.filter(book=book, source_type=ct)
                   .values_list("source_id", flat=True))

        w(f"Book {book.pk}: {book.name}   cutover {cutover}")
        w(f"  movements: {len(movements)}   already posted: {len(done)}")

        try:
            with transaction.atomic():
                posted, skipped, refused = 0, 0, {}
                for mv in movements:
                    if mv.pk in done:
                        skipped += 1
                        continue
                    try:
                        if post_movement(mv, reference=ref):
                            posted += 1
                        else:
                            skipped += 1          # zero-value movement
                    except NoRuleFor:
                        refused[mv.movement_type] = refused.get(
                            mv.movement_type, 0) + 1

                # The movement loop dedupes on source_id, but these two
                # carry no source row, so they need their own guard or a
                # second run posts the stock and the reclass twice over —
                # assets climbed 1,600 to 2,150 in the test that found it.
                already = set(
                    JournalEntry.objects.filter(book=book, reference=ref)
                    .values_list("description", flat=True))
                # Cash rows whose source is not a Payment: a Payment's cash
                # leg already rides on its current-account movement above.
                from accounting.models import CashTransactionEntry
                from accounting.services_posting import post_cash_entry
                cash_done = set(
                    JournalEntry.objects.filter(book=book, reference=ref)
                    .exclude(source_type=ct).values_list("source_id", flat=True))
                cash_posted = 0
                for ce in CashTransactionEntry.objects.filter(book=book):
                    name = ContentType.objects.get(pk=ce.content_type_id).model
                    if name not in CASH_CONTRA_BY_SOURCE:
                        continue
                    if ce.content_pk in cash_done:
                        continue
                    if post_cash_entry(ce, reference=ref):
                        cash_posted += 1
                if cash_posted:
                    w(f"  posted {cash_posted} cash event(s)")

                inv = reclass = None
                unvalued_n, unvalued_qty, reclass_n = 0, 0, 0
                if "Opening inventory" not in already:
                    inv, unvalued_n, unvalued_qty = post_opening_inventory(
                        book, date=cutover, reference=ref)
                if "Reclassify credit balances to accounts payable" not in already:
                    reclass, reclass_n = reclassify_payables(
                        book, date=cutover, reference=ref)

                w(f"  posted {posted}, skipped {skipped}")
                for kind, n in sorted(refused.items()):
                    w(self.style.WARNING(
                        f"  REFUSED {n} x {kind} — no rule; decide its contra "
                        f"in services_posting.CONTRA_BY_TYPE"))
                if inv:
                    w(f"  opening inventory: {inv.lines.first().debit}")
                if unvalued_n:
                    w(self.style.WARNING(
                        f"  {unvalued_n} items ({unvalued_qty}) carry no cost "
                        f"and are outside that figure"))
                if reclass:
                    w(f"  reclassified {reclass_n} credit-balance accounts")

                self._report(book, w)
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. Re-run with --apply."))
            return
        w(self.style.SUCCESS(f"\nCommitted. Undo with reference={ref!r}."))

    def _report(self, book, w):
        """The two columns, side by side, the way the page shows them."""
        gl = balance_sheet(book)
        subs = subsidiary_equation(book)
        w("")
        w(f"  {'':<14}{'GENERAL LEDGER':>18}{'SUBSIDIARY':>18}")
        for label, key in (("assets", "assets"), ("liabilities", "liabilities"),
                           ("equity", "equity")):
            w(f"  {label:<14}{gl[key]:>18}{subs[key]:>18}")
        w(f"  {'balanced':<14}{str(gl['balanced']):>18}{str(subs['balanced']):>18}")
        if subs["assets"]:
            pct = (gl["assets"] / subs["assets"] * 100).quantize(Decimal("0.1"))
            w(f"  {'coverage':<14}{str(pct) + '%':>18}")
