"""Ask the ledger the questions it is supposed to be able to answer.

Four of them, in order of how bad a "no" would be:

  1. Does every entry balance? It cannot not — post_entry refuses an
     unbalanced one — so a failure here means something wrote lines by a
     route that is not post_entry, and nothing else in this report can be
     trusted until that is explained.

  2. Does the trial balance balance? The same question asked of the whole
     book at once.

  3. Does the accounting equation hold? Assets against liabilities plus
     equity, with the period's result folded in.

  4. Does each control account equal the ledger it summarises? This is the
     one that can legitimately say no while the migration is unfinished,
     and it names what is missing rather than merely how much.

Exits non-zero when any of the first three fails, so it can be run on a
schedule and be silent while it is happy. A control account that has not
caught up is reported but does not fail the run — that is work outstanding,
not a broken ledger — unless --strict says otherwise.

    python manage.py audit_ledger              # every book
    python manage.py audit_ledger --book 5
    python manage.py audit_ledger --strict     # reconciliation must agree too
"""
from django.core.management.base import BaseCommand, CommandError

from accounting.models import Book
from accounting.services_ledger import (balance_sheet, reconcile,
                                        unbalanced_entries)


def _money(value):
    return f"{value:>16,.2f}"


class Command(BaseCommand):
    help = "Check that the ledger balances and that the control accounts agree."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int, default=None,
                            help="One book id. Default: every book.")
        parser.add_argument("--date-to", default=None,
                            help="Report as at this date (YYYY-MM-DD).")
        parser.add_argument("--strict", action="store_true",
                            help="Fail when a control account has not caught "
                                 "up, not only when the ledger is unsound.")

    def handle(self, *args, **opts):
        books = Book.objects.all()
        if opts["book"] is not None:
            books = books.filter(pk=opts["book"])
            if not books.exists():
                raise CommandError(f"No book with id {opts['book']}.")

        date_to = opts["date_to"]
        unsound, unreconciled = [], []

        for book in books:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n{book.name} (book {book.pk})"))

            bad = unbalanced_entries(book)
            if bad:
                unsound.append(book)
                self.stdout.write(self.style.ERROR(
                    f"  {len(bad)} entr{'y' if len(bad) == 1 else 'ies'} do "
                    f"not balance — written by something other than "
                    f"post_entry:"))
                for row in bad[:10]:
                    self.stdout.write(self.style.ERROR(
                        f"    #{row['entry'].pk} {row['entry'].date} "
                        f"out by {row['difference']}"))
            else:
                self.stdout.write("  every entry balances")

            gl = balance_sheet(book, date_to=date_to)
            tb = gl["trial_balance"]
            if tb["balanced"]:
                self.stdout.write(
                    f"  trial balance balances at {_money(tb['total_debit'])}")
            else:
                unsound.append(book)
                self.stdout.write(self.style.ERROR(
                    f"  trial balance is out by {tb['difference']}"))

            self.stdout.write(f"  assets      {_money(gl['assets'])}")
            self.stdout.write(f"  liabilities {_money(gl['liabilities'])}")
            self.stdout.write(f"  equity      {_money(gl['equity'])}"
                              f"   (result for the period {gl['result']})")
            if gl["balanced"]:
                self.stdout.write(self.style.SUCCESS(
                    "  assets = liabilities + equity"))
            else:
                unsound.append(book)
                self.stdout.write(self.style.ERROR(
                    f"  the equation is out by {gl['difference']}"))

            rec = reconcile(book, date_to=date_to)
            self.stdout.write("\n  control accounts")
            for row in rec["rows"]:
                mark = "ok " if row["reconciled"] else "OUT"
                style = self.style.SUCCESS if row["reconciled"] else self.style.WARNING
                self.stdout.write(style(
                    f"    {mark} {row['label']:<26} {row['control']:<12}"
                    f"{_money(row['ledger'])}{_money(row['subsidiary'])}"
                    f"{_money(row['difference'])}"))
                if not row["reconciled"] and row["note"]:
                    self.stdout.write(f"        {row['note']}")
            if not rec["all_reconciled"]:
                unreconciled.append(book)

            if rec["pending"]:
                self.stdout.write("\n  waiting to be classified")
                for row in rec["pending"]:
                    self.stdout.write(
                        f"    {row['code']} {row['label']:<26}"
                        f"{_money(row['balance'])}")
                    self.stdout.write(f"        {row['note']}")

        if unsound:
            raise CommandError(
                "The ledger is unsound on: "
                + ", ".join(sorted({b.name for b in unsound})))
        if unreconciled and opts["strict"]:
            raise CommandError(
                "Control accounts have not caught up on: "
                + ", ".join(sorted({b.name for b in unreconciled})))
        self.stdout.write(self.style.SUCCESS("\nThe ledger is sound."))
