"""Pair two inter-company accounts so each mirrors the other.

    python manage.py pair_mirror_accounts 142 1622          # dry run
    python manage.py pair_mirror_accounts 142 1622 --apply

From the moment of pairing, every movement created on either account is
written onto the other with the opposite sign (see services_mirror). Rows
already there are not copied: pair only accounts whose balances agree, and
the command refuses otherwise.
"""
from django.core.management.base import BaseCommand, CommandError

from accounting.models_accounts import CurrentAccount
from accounting.services_mirror import pair_accounts


class Command(BaseCommand):
    help = "Pair two inter-company accounts in different books so they mirror each other."

    def add_arguments(self, parser):
        parser.add_argument("first", type=int, help="Account id in one book.")
        parser.add_argument("second", type=int, help="Account id in the other book.")
        parser.add_argument("--apply", action="store_true", help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        try:
            first = CurrentAccount.objects.select_related("book").get(pk=opts["first"])
            second = CurrentAccount.objects.select_related("book").get(pk=opts["second"])
        except CurrentAccount.DoesNotExist as exc:
            raise CommandError(str(exc))

        a, b = first.recompute_balance(), second.recompute_balance()
        self.stdout.write(f"{first.book.name}: {first}  balance {a}")
        self.stdout.write(f"{second.book.name}: {second}  balance {b}")
        if a + b != 0:
            raise CommandError(
                f"The balances don't mirror each other (they add up to {a + b}, not 0). "
                "Reconcile them before pairing, or every later movement starts from a gap.")
        if not opts["apply"]:
            self.stdout.write("Dry run — nothing changed. Re-run with --apply.")
            return
        since = pair_accounts(first, second)
        self.stdout.write(self.style.SUCCESS(f"Paired. Movements created from {since:%Y-%m-%d %H:%M:%S %Z} on are mirrored."))
