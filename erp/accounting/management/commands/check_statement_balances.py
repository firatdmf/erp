"""Detect accounts whose cached balance has drifted from their ledger.

`CurrentAccount.cached_balance` is a cache, kept in step by
CurrentAccountMovement.save() and recompute_balance(). Anything that writes rows
around those — a bulk update, a migration, a hand repair in a shell —
leaves it stale, and a stale balance is invisible: the number simply
looks like a number.

This recomputes each account from its live movements and reports any
that disagree.

    python manage.py check_statement_balances          # report
    python manage.py check_statement_balances --fix    # and repair

Read-only without --fix. Exits non-zero when anything diverges, so CI or
a cron can fail on it rather than someone noticing months later.

It no longer has to check the statement against the account page. Those
were two computations that agreed only by argument until migration 0086;
both now sum CurrentAccountMovementQuerySet.live(), so they cannot differ. What is
left to check is whether the cache matches the rows.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from accounting.models import CurrentAccount


class Command(BaseCommand):
    help = "Report (or repair) accounts whose cached balance has drifted."

    def add_arguments(self, parser):
        parser.add_argument(
            "--book", type=int, default=None,
            help="Restrict to one book's accounts.",
        )
        parser.add_argument(
            "--fix", action="store_true",
            help="Recompute and save the accounts that disagree.",
        )

    def handle(self, *args, **options):
        accounts = CurrentAccount.objects.all().order_by("book_id", "code")
        if options["book"]:
            accounts = accounts.filter(book_id=options["book"])

        bad = []
        checked = 0
        for current_account in accounts.iterator():
            checked += 1
            actual = (current_account.movements.live()
                      .aggregate(s=Sum("amount_base"))["s"] or Decimal("0.00"))
            if actual != current_account.cached_balance:
                bad.append((current_account, actual))

        if not bad:
            self.stdout.write(self.style.SUCCESS(
                f"{checked} accounts checked — every cached balance matches "
                f"its ledger."
            ))
            return

        self.stdout.write(self.style.ERROR(
            f"{len(bad)} of {checked} accounts have a stale cached balance:"
        ))
        for current_account, actual in bad:
            self.stdout.write(
                f"  #{current_account.pk} {current_account.code} {current_account.name}\n"
                f"      cached  {current_account.cached_balance}\n"
                f"      ledger  {actual}\n"
                f"      drift   {actual - current_account.cached_balance}"
            )

        if options["fix"]:
            for current_account, _actual in bad:
                current_account.recompute_balance(save=True)
            self.stdout.write(self.style.SUCCESS(
                f"Recomputed {len(bad)} accounts."
            ))
            return

        raise SystemExit(1)
