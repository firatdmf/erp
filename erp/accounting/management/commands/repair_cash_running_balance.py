"""Backfill the cash ledger rows that payments never wrote, and check it adds up.

A payment moves cash by writing straight to CashAccount.balance. It used to
record nothing in CashTransactionEntry, so money moved that the transactions
page never showed — book 2's ledger was missing $1,745 of collections that
way. Payment.sync_cash_entry() now writes those rows as they happen, from
confirm, from the edit view and from cancel; this command catches up anything
recorded before that existed.

It then checks the invariant that makes the ledger trustworthy: summing a
cash account's entries from zero should land exactly on the account's own
balance. If it does not, something is still moving cash without writing here,
and the difference is reported rather than papered over.

Running balances are no longer stored, so there is nothing to recompute —
the transactions page derives them from the rows every time it renders them
(views.running_cash_balances). This command's job is only to make sure the
rows themselves are all present.

Dry run by default — pass --apply to write.
"""

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models import Book, CashAccount, CashTransactionEntry
from accounting.models_accounts import Payment


class Command(BaseCommand):
    help = "Backfill missing payment cash entries and verify the ledger adds up."

    def add_arguments(self, parser):
        parser.add_argument(
            "--book",
            type=int,
            default=None,
            help="Only repair this book (default: every book with entries).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the changes. Without it the command only reports.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        book_ids = (
            [options["book"]]
            if options["book"]
            else sorted(
                set(
                    CashTransactionEntry.objects.values_list("book_id", flat=True)
                ).union(
                    Payment.objects.filter(
                        status="confirmed", cash_account__isnull=False
                    ).values_list("book_id", flat=True)
                )
            )
        )

        for book_id in book_ids:
            book = Book.objects.get(pk=book_id)
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nBook {book_id} ({book})"))
            pending = self._backfill(book, apply_changes)
            self._verify(book, pending)

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING("\nDry run — re-run with --apply to write.")
            )

    # ------------------------------------------------------------------
    def _backfill(self, book, apply_changes):
        """Write the entry for every confirmed payment that lacks one.

        Cancelled payments are skipped: their cash was reversed, so on net
        they moved nothing and have no place in the ledger.
        """
        payment_ct = ContentType.objects.get_for_model(Payment)
        already = set(
            CashTransactionEntry.objects.filter(
                book=book, content_type=payment_ct
            ).values_list("content_pk", flat=True)
        )

        missing = [
            p
            for p in Payment.objects.filter(
                book=book, status="confirmed", cash_account__isnull=False
            ).order_by("date", "pk")
            if p.pk not in already
        ]

        if not missing:
            self.stdout.write("  backfill: nothing missing.")
            return []

        for p in missing:
            sign = "+" if p.cash_sign > 0 else "−"
            self.stdout.write(
                f"  backfill: payment {p.pk} {p.date} {p.movement_type} "
                f"{sign}{p.amount} {p.currency.code} → {p.cash_account.name}"
            )

        if not apply_changes:
            return missing

        with transaction.atomic():
            for p in missing:
                entry = p.sync_cash_entry()
                # created_at is auto_now_add and would claim the backfill
                # happened now. `date` already files the row under the day
                # the money moved; this puts the recorded-at stamp right too.
                if entry is not None:
                    CashTransactionEntry.objects.filter(pk=entry.pk).update(
                        created_at=p.created_at
                    )
        return []

    # ------------------------------------------------------------------
    def _verify(self, book, pending):
        """Does each account equal the sum of its own entries?

        `pending` are rows a dry run would have written but did not, so their
        amounts are counted here too — otherwise a preview would report a
        mismatch that applying would not actually leave behind.
        """
        sums = {}
        rows = CashTransactionEntry.objects.filter(book=book).values_list(
            "cash_account_id", "amount", "is_amount_positive"
        )
        for account_id, amount, positive in rows:
            if account_id is None:
                continue
            delta = (amount or Decimal("0.00")) * (1 if positive else -1)
            sums[account_id] = sums.get(account_id, Decimal("0.00")) + delta

        for p in pending:
            delta = p.amount * Decimal(p.cash_sign)
            sums[p.cash_account_id] = (
                sums.get(p.cash_account_id, Decimal("0.00")) + delta
            )

        ok = True
        for account in CashAccount.objects.filter(book=book).select_related("currency"):
            summed = sums.get(account.pk, Decimal("0.00"))
            if summed != account.balance:
                ok = False
                self.stdout.write(
                    self.style.ERROR(
                        f"  MISMATCH {account.name} {account.currency.code}: "
                        f"ledger sums to {summed}, account holds {account.balance} "
                        f"(difference {account.balance - summed}) — something moves "
                        f"this account without writing a cash entry."
                    )
                )
        if ok:
            self.stdout.write(
                self.style.SUCCESS(
                    "  verified: every cash account equals the sum of its entries."
                )
            )
