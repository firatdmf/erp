"""Make the cash ledger a complete record, then recompute its running total.

CashTransactionEntry.total_base_currency_balance is the book's total cash in
base currency after each row. It used to be chained off the previous row's
stored value, which drifts, because this table was never the only thing that
moved cash: Payment.post() writes straight to CashAccount.balance with a raw
F() UPDATE (models_accounts.Payment) and records nothing here. Book 2's newest
row read $59.60 against a real $1,804.98.

CashTransactionEntry.save() now stamps new rows from the live cash accounts,
so the drift stops there. This command repairs what is already stored, in two
phases:

  1. Backfill — write the missing entry for every confirmed Payment that named
     a cash account. Cancelled payments are skipped: their cash was reversed,
     so they moved nothing on net. Each backfilled row is dated from the
     payment itself so it sorts into its true place in the list.

  2. Recompute — walk every row of the book oldest → newest and accumulate the
     signed amounts, setting both cash_account_balance (per account) and
     total_base_currency_balance (per book) from zero.

Phase 2 is only meaningful once phase 1 has made the ledger complete; the
check at the end confirms it, by comparing the accumulated per-account totals
against the live CashAccount.balance values. If those disagree, something
still moves cash without writing here and the mismatch is reported rather
than papered over.

The recomputed book total uses each row's amount_in_base_currency, which was
converted at the rate in force when the row was written. It will therefore sit
a little away from the dashboard's live figure, which converts today's
balances at today's rate. That gap is real and is reported, not hidden.

Dry run by default — pass --apply to write.
"""

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models import Book, CashAccount, CashTransactionEntry
from accounting.models_accounts import Payment


class Command(BaseCommand):
    help = "Backfill payment cash entries and recompute running balances."

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
        from accounting.views import get_total_base_currency_balance

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
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\nBook {book_id} ({book})")
            )
            pending = self._backfill(book, apply_changes)
            # On a dry run the phase-1 rows were not written, so splice them
            # into phase 2's view of the ledger. Without that the preview
            # recomputes a ledger still missing the payments and reports a
            # mismatch that applying would not actually produce.
            self._recompute(
                book, apply_changes, get_total_base_currency_balance, pending
            )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING("\nDry run — re-run with --apply to write.")
            )

    # ------------------------------------------------------------------
    # Phase 1
    # ------------------------------------------------------------------
    def _backfill(self, book, apply_changes):
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
                entry = CashTransactionEntry.objects.create(
                    book=book,
                    content_type=payment_ct,
                    content_pk=p.pk,
                    amount=p.amount,
                    is_amount_positive=p.cash_sign > 0,
                    currency=p.currency,
                    cash_account=p.cash_account,
                )
                # `date` is derived from the payment, so the row already
                # files under the right day. created_at is auto_now_add and
                # would claim the backfill happened now; point it at when the
                # payment was actually recorded instead.
                CashTransactionEntry.objects.filter(pk=entry.pk).update(
                    created_at=p.created_at
                )
        return []

    # ------------------------------------------------------------------
    # Phase 2
    # ------------------------------------------------------------------
    def _recompute(
        self, book, apply_changes, get_total_base_currency_balance, pending=()
    ):
        entries = list(
            CashTransactionEntry.objects.filter(book=book)
            .select_related("cash_account", "currency")
            .order_by("date", "created_at", "pk")
        )
        entries.extend(self._preview_rows(book, pending))
        entries.sort(key=lambda e: (e.date, e.created_at, e.pk or 0))

        if not entries:
            self.stdout.write("  recompute: no entries.")
            return

        per_account = {}
        book_total = Decimal("0.00")
        planned = []

        for e in entries:
            amount = e.amount or Decimal("0.00")
            base = e.amount_in_base_currency or Decimal("0.00")
            if not e.is_amount_positive:
                amount, base = -amount, -base

            acct_id = e.cash_account_id
            if acct_id is not None:
                per_account[acct_id] = per_account.get(acct_id, Decimal("0.00")) + amount
            book_total += base

            new_acct_balance = per_account.get(acct_id) if acct_id else None
            if e.pk is None:
                # A phase-1 row previewed on a dry run: it counts towards the
                # totals but there is nothing to update.
                self.stdout.write(
                    f"  entry NEW (payment {e.content_pk}): account "
                    f"→ {new_acct_balance}, book → {book_total}"
                )
                continue
            if (
                e.total_base_currency_balance != book_total
                or (acct_id and e.cash_account_balance != new_acct_balance)
            ):
                planned.append((e, new_acct_balance, book_total))

        for e, acct_balance, total in planned:
            self.stdout.write(
                f"  entry {e.pk}: account {e.cash_account_balance} → {acct_balance}, "
                f"book {e.total_base_currency_balance} → {total}"
            )

        if planned and apply_changes:
            with transaction.atomic():
                for e, acct_balance, total in planned:
                    CashTransactionEntry.objects.filter(pk=e.pk).update(
                        cash_account_balance=acct_balance,
                        total_base_currency_balance=total,
                    )
        elif not planned:
            self.stdout.write("  recompute: already correct.")

        self._verify(book, per_account, book_total, get_total_base_currency_balance)

    # ------------------------------------------------------------------
    def _preview_rows(self, book, pending):
        """Unsaved stand-ins for the phase-1 rows, so a dry run adds up."""
        from accounting.models import get_base_currency
        from accounting.services import get_exchange_rate

        base = get_base_currency()
        rows = []
        for p in pending:
            if p.currency.code == base.code:
                in_base = p.amount
            else:
                rate = get_exchange_rate(p.currency.code, base.code)
                in_base = (p.amount * rate).quantize(Decimal("0.01")) if rate else None
            rows.append(
                CashTransactionEntry(
                    book=book,
                    content_pk=p.pk,
                    amount=p.amount,
                    is_amount_positive=p.cash_sign > 0,
                    currency=p.currency,
                    cash_account=p.cash_account,
                    amount_in_base_currency=in_base,
                    date=p.date,
                    created_at=p.created_at,
                )
            )
        return rows

    # ------------------------------------------------------------------
    def _verify(self, book, per_account, book_total, get_total_base_currency_balance):
        """Does the ledger, summed from zero, reproduce the live balances?"""
        ok = True
        for account in CashAccount.objects.filter(book=book):
            summed = per_account.get(account.pk, Decimal("0.00"))
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

        live = get_total_base_currency_balance(book_pk=book.pk)
        self.stdout.write(
            f"  book total: ledger {book_total} vs live {live} "
            f"(difference {live - book_total} — FX timing, see module docstring)"
        )
