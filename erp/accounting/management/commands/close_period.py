"""Close a book's period: empty the temporary accounts into Retained Earnings.

Revenue, expenses and dividends each collect one period's worth and are
then meant to be emptied, leaving Retained Earnings as the permanent record
of what the business has kept. Nothing emptied them, so they would have
accumulated indefinitely: by the end of a second year account 4000 would
hold two years of sales and 3300 two years of distributions, with nothing
on the page able to say which year either belonged to.

The balance sheet stays correct either way — it folds revenue less expenses
into equity as the period's result — so this changes no total. It is the
PERIOD figures that rot without it: "profit this year" quietly becomes
profit since the beginning of time.

Equity does not move. What was reported as the period's result becomes part
of Retained Earnings instead, which is the same number in a different place.

The entry is tagged, so a close can be undone:

    JournalEntry.objects.filter(reference="CLOSE-5-2026-12-31").delete()

Safe to re-run: the entry zeroes each account, so a later run only sees
what has accumulated since.

Dry run by default; pass --apply to commit.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from accounting.models import Book
from accounting.services_ledger import balance_sheet, ensure_chart
from accounting.services_posting import RETAINED_EARNINGS, close_period


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Close a book's temporary accounts into Retained Earnings."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int, required=True)
        parser.add_argument("--through", required=True,
                            help="Last date in the period, e.g. 2026-12-31.")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        from django.db import transaction

        w = self.stdout.write
        try:
            book = Book.objects.get(pk=opts["book"])
        except Book.DoesNotExist:
            raise CommandError(f"No book with id {opts['book']}.")
        through = opts["through"]
        ref = f"CLOSE-{book.pk}-{through}"
        ensure_chart()

        before = balance_sheet(book, date_to=through)
        w(f"{book.name} — closing through {through}")
        w(f"  equity before  {before['equity']}")

        try:
            with transaction.atomic():
                entry, balances = close_period(
                    book, date_to=through, reference=ref)
                if entry is None:
                    w(self.style.NOTICE(
                        "  Nothing to close — no revenue, expense or dividend "
                        "balance stands at that date."))
                    return

                w("  emptied:")
                for code, net in sorted(balances.items()):
                    side = "debit" if net > 0 else "credit"
                    w(f"     {code}  {abs(net):>14}  ({side} balance)")
                plug = next(l for l in entry.lines.all()
                            if l.account.code == RETAINED_EARNINGS)
                moved = plug.debit or plug.credit
                keeps = "kept" if plug.credit else "lost"
                w(f"  {RETAINED_EARNINGS} Retained Earnings  {moved}  ({keeps})")

                after = balance_sheet(book, date_to=through)
                w(f"  equity after   {after['equity']}"
                  f"   unchanged: {after['equity'] == before['equity']}")
                w(f"  still balanced: {after['balanced']}")

                # What the next period opens with. There is no opening
                # entry to post: the ledger is cumulative and every
                # statement is a date filter over it, so the day after a
                # close already shows the permanent accounts carried
                # forward and the temporary ones at zero.
                w("")
                w("  the next period opens with:")
                for r in after["trial_balance"]["rows"]:
                    if r["balance"]:
                        w(f"     {r['code']}  {r['name']:<26} {r['balance']:>14}")
                w(f"           {'assets':<26} {after['assets']:>14}")
                w(f"           {'liabilities + equity':<26} "
                  f"{after['liabilities_plus_equity']:>14}")
                if after["equity"] != before["equity"]:
                    raise CommandError(
                        "Equity moved — a close must only relocate the result, "
                        "never change it.")
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. "
                                "Re-run with --apply."))
            return
        w(self.style.SUCCESS(f"\nCommitted. Undo with reference={ref!r}."))
