"""Record every foreign account's exchange difference, at month end.

A foreign balance is booked at the rate of each movement's own day, so as
the rate moves the book carries it at a price nobody would pay. The
account page shows that gap and has a button for it, but a gap nobody
presses the button for does not stay harmless: when the customer finally
settles, their own-currency balance reaches zero while the base figure
keeps the difference, and the account reads "We Owe" for money nobody owes
anybody. Left alone they accumulate, 1200 stops reconciling against what
customers actually owe, and a real FX loss hides inside the receivable
instead of reaching 5900 where it can be read.

So the same posting the button makes, made for every account at once, on
the day the period ends.

Run by a daily scheduler: it does nothing on the other days, so the cron
entry is simply

    python manage.py sweep_fx --apply

and the command itself decides that today is the last day of the month.
Pass --force to record on some other day, --date to state the day, and
--book to limit it to one book.

Dry run by default: it prints what it would record and posts nothing.
Safe to re-run — a second run on the same day finds the gap already
closed, and skips an account that already carries an entry for that date.
"""
from calendar import monthrange
from datetime import date as _date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Book
from accounting.models_accounts import CurrentAccountMovement, CurrentAccount
from accounting.services_fx import fx_position, is_foreign, post_fx_difference


def _is_month_end(day):
    return day.day == monthrange(day.year, day.month)[1]


class Command(BaseCommand):
    help = "Record each foreign-currency account's exchange difference (month end)."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int,
                            help="Only this book; default is every book.")
        parser.add_argument("--date", help="The day to record on, e.g. 2026-09-30.")
        parser.add_argument("--force", action="store_true",
                            help="Record even when the date is not a month end.")
        parser.add_argument("--apply", action="store_true",
                            help="Actually record; without it nothing is written.")

    def handle(self, *args, **options):
        when = options.get("date")
        try:
            day = (datetime.strptime(when, "%Y-%m-%d").date() if when else _date.today())
        except ValueError:
            raise CommandError("--date must look like 2026-09-30.")

        if not _is_month_end(day) and not options["force"]:
            # The ordinary outcome of a daily cron on the other 30 days.
            self.stdout.write(f"{day} is not a month end — nothing to do.")
            return

        books = (Book.objects.filter(pk=options["book"]) if options.get("book")
                 else Book.objects.all())
        if options.get("book") and not books.exists():
            raise CommandError(f"No book with id {options['book']}.")

        apply_ = options["apply"]
        total, posted, skipped = Decimal("0.00"), 0, 0
        for book in books.order_by("name"):
            accounts = (CurrentAccount.objects.filter(book=book, is_active=True)
                        .select_related("default_currency", "book").order_by("name"))
            for account in accounts:
                if not is_foreign(account):
                    continue
                position = fx_position(account)
                if not position:
                    continue
                if position.get("unavailable"):
                    self.stdout.write(self.style.WARNING(
                        f"  {book.name} · {account.name}: no rate today — skipped"))
                    skipped += 1
                    continue
                difference = position["difference"]
                if difference == Decimal("0.00"):
                    continue
                # An account already recorded on this day is left alone, so a
                # second run in the same period adds nothing.
                if CurrentAccountMovement.objects.filter(
                        current_account=account, movement_type="fx_adjustment",
                        date=day).exists():
                    self.stdout.write(
                        f"  {book.name} · {account.name}: already recorded on {day}")
                    skipped += 1
                    continue

                self.stdout.write(
                    f"  {book.name} · {account.name}: {position['symbol']}"
                    f"{position['own_balance']} owed, carried "
                    f"{position['base_code']} {position['base_balance']}, worth "
                    f"{position['base_at_rate']} at {position['rate']} → "
                    f"{'+' if difference > 0 else ''}{difference}")
                total += difference
                posted += 1
                if apply_:
                    with transaction.atomic():
                        post_fx_difference(account, on_date=day, position=position)

        head = "Recorded" if apply_ else "Would record"
        self.stdout.write(self.style.SUCCESS(
            f"{head} {posted} difference(s) on {day}, netting "
            f"{'+' if total > 0 else ''}{total}."
            + (f" {skipped} skipped." if skipped else "")))
        if not apply_:
            self.stdout.write("Nothing was written — pass --apply to record.")
