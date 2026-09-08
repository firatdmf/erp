"""Record what happened to the NADYA collection: it was taken as a dividend.

Payment 123 collected $1,500.00 from NADYA RUSYA 2024 on 2026-09-03. The
money never sat in a drawer — it went straight out to the owners — and the
second half of that was never written down: EquityDivident has no rows at
all, and Ergene's three cash accounts show no entries against them.

So the books recorded the customer paying and nothing else. The general
ledger, replaying what was recorded, posted the collection as debt turning
into cash and left $1,500 sitting in account 1000 that nobody holds. That
is the whole of the 0.1% by which the ledger exceeded the subsidiary
ledgers.

This writes both legs, through the same code the equity screens use:

  1. the payment names the cash account the money landed in, which is what
     makes the collection's existing posting true rather than a fiction
  2. an EquityDivident takes it straight back out again

Cash nets to zero, which is what actually happened, and equity falls by
$1,500, which is what a dividend does. Re-runnable: it does nothing if the
dividend is already there.

Dry run by default; pass --apply to commit.
"""
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Book, CashAccount, CashTransactionEntry
from accounting.models_accounts import Payment
from accounting.views import handle_equity_transaction

PAYMENT_PK = 123
CASH_ACCOUNT_PK = 26          # Ergene Fabric · Cash · USD
MARKER = "Collection from NADYA RUSYA 2024 taken as dividend"


class Command(BaseCommand):
    help = "Record the NADYA collection's missing dividend leg."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        w = self.stdout.write
        EquityDivident = apps.get_model("accounting", "EquityDivident")

        payment = Payment.objects.filter(pk=PAYMENT_PK).first()
        if payment is None:
            raise CommandError(f"No payment {PAYMENT_PK}.")
        cash = CashAccount.objects.filter(pk=CASH_ACCOUNT_PK).first()
        if cash is None:
            raise CommandError(f"No cash account {CASH_ACCOUNT_PK}.")
        if cash.currency_id != payment.currency_id:
            raise CommandError(
                f"Cash account is {cash.currency} but the payment is "
                f"{payment.currency}.")
        if EquityDivident.objects.filter(description=MARKER).exists():
            w(self.style.NOTICE("Already recorded — nothing to do."))
            return

        book = payment.book
        w(f"payment {payment.pk}: {payment.amount} {payment.currency.code} "
          f"on {payment.date}, method={payment.method}, "
          f"cash_account={payment.cash_account}")
        w(f"cash account {cash.pk} ({cash.currency.code}) balance "
          f"{cash.balance}")

        try:
            with transaction.atomic():
                cash.balance = (cash.balance or Decimal("0")) + payment.amount
                cash.save(update_fields=["balance"])
                payment.cash_account = cash
                payment.save(update_fields=["cash_account"])
                payment.sync_cash_entry()

                dividend = EquityDivident.objects.create(
                    book=book, member=payment.created_by, cash_account=cash,
                    currency=payment.currency, amount=payment.amount,
                    date=payment.date, description=MARKER)
                handle_equity_transaction(book, payment.amount,
                                          payment.currency, dividend,
                                          dividend.pk, cash)

                cash.refresh_from_db()
                w(f"  dividend id {dividend.pk}")
                w(f"  cash account balance now {cash.balance}")
                for e in CashTransactionEntry.objects.filter(book=book):
                    sign = "+" if e.is_amount_positive else "-"
                    w(f"    {e.date}  {sign}{e.amount}  {e.content_type.model}")
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. "
                                "Re-run with --apply."))
            return
        w(self.style.SUCCESS("\nCommitted."))


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""
