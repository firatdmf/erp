"""Record the typed-rate differences of payments confirmed before the
ledger recorded them on its own.

A payment taken at a typed rate settles the account at one figure while
the money was worth another, and the gap now reaches 5900 the moment the
payment posts (services_posting.lines_for_movement). Payments confirmed
before that carry no photograph of the published rate for their day, so
their entries show two lines where three are due, and their cash rows are
carried at the typed rate rather than at what the money was worth.

This gives each such payment its published rate, re-posts its entry and
re-converts its cash row — through the same code a fresh confirmation
runs, so a backfilled payment and a new one cannot disagree.

Dry run by default: it prints what it would do and writes nothing. Safe
to re-run — a payment already photographed is skipped.

    python manage.py backfill_realised_fx            # look
    python manage.py backfill_realised_fx --apply    # do
    python manage.py backfill_realised_fx --book 2   # one book
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models_accounts import Payment
from accounting.services_fx import realised_fx
from accounting.services_posting import post_movement


class Command(BaseCommand):
    help = "Photograph the published rate on payments taken at a typed rate, and post the difference."

    def add_arguments(self, parser):
        parser.add_argument("--book", type=int, help="Only this book; default is every book.")
        parser.add_argument("--apply", action="store_true",
                            help="Actually write; without it nothing changes.")

    def handle(self, *args, **options):
        base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
        payments = (Payment.objects
                    .filter(status="confirmed", exchange_rate__isnull=False,
                            published_rate__isnull=True)
                    .exclude(currency__code=base_code)
                    .select_related("book", "currency", "current_account", "posted_movement")
                    .order_by("book_id", "date", "id"))
        if options["book"]:
            payments = payments.filter(book_id=options["book"])

        total = Decimal("0.00")
        touched = skipped = 0
        for payment in payments:
            with transaction.atomic():
                published = payment._published_rate_for_date()
                if published is None:
                    skipped += 1
                    self.stdout.write(f"  {payment.number}  {payment.date}  no published rate for "
                                      f"{payment.currency.code} — left alone")
                    continue
                payment.published_rate = published
                fx = realised_fx(payment)
                gain = fx["difference"] if fx else Decimal("0.00")
                self.stdout.write(
                    f"  {payment.number}  {payment.date}  {payment.get_type_display()}  "
                    f"{payment.amount} {payment.currency.code}  typed {payment.exchange_rate.normalize()}  "
                    f"published {published.normalize()}  → {gain:+} {base_code}  |  "
                    f"{payment.current_account.name} ({payment.book.name})")
                total += gain
                touched += 1
                if not options["apply"]:
                    continue
                Payment.objects.filter(pk=payment.pk).update(published_rate=published)
                if payment.posted_movement_id:
                    post_movement(payment.posted_movement)
                # Re-converts the kasa row at what the money was worth.
                payment.sync_cash_entry()

        verb = "recorded" if options["apply"] else "would record"
        self.stdout.write(self.style.SUCCESS(
            f"{touched} payment(s) {verb}, net {total:+} {base_code}; {skipped} without a published rate."))
        if not options["apply"]:
            self.stdout.write("Dry run — pass --apply to write.")
