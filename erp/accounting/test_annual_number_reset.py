"""Every numbered document restarts at 1 when the year turns.

The number already carried the year — INV-2026-000108, COL-2026-000101,
ORD-2026-000001 — but the sequence ran straight on underneath it, so the
first invoice of 2027 would have been INV-2027-000109. The year said one
thing and the count said another.

They restart now. What that costs is the guarantee that a tail is unique
on its own: INV-2027-000001 and INV-2026-000001 are different documents
and only the year tells them apart. That is the ordinary convention for
issued paperwork, and it is what was asked for.

Numbers already issued are never touched. The reset only decides what the
NEXT one is.

The current-account code is deliberately outside all of this: ACC-088
carries no year, so restarting it would hand out a code the book already
has. There is a test below that says so.

Run with:
    python manage.py test accounting.test_annual_number_reset
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccountSettings
from accounting.views_payment import _next_payment_number
from operating.models import Order, OrderNumberSequence


def in_year(year):
    """A now() fixed to `year`, built before any patch is active."""
    return patch("django.utils.timezone.now",
                 return_value=timezone.now().replace(year=year))


class TheCountersRestart(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.settings = CurrentAccountSettings.for_book(self.book)

    def test_collections_restart(self):
        first = _next_payment_number(self.book, "collection")
        _next_payment_number(self.book, "collection")
        self.assertTrue(first.endswith("-000001"))
        with in_year(2031):
            new_year = _next_payment_number(self.book, "collection")
        self.assertEqual(new_year, "COL-2031-000001")

    def test_payments_share_that_run(self):
        """COL and PAY come off one counter, so they restart together and
        neither reuses a tail the other issued."""
        _next_payment_number(self.book, "collection")
        with in_year(2031):
            first = _next_payment_number(self.book, "payment")
            second = _next_payment_number(self.book, "collection")
        self.assertEqual(first, "PAY-2031-000001")
        self.assertEqual(second, "COL-2031-000002")

    def test_invoices_restart(self):
        self.settings.next_invoice_number()
        self.settings.next_invoice_number()
        with in_year(2031):
            self.assertEqual(self.settings.next_invoice_number(),
                             "INV-2031-000001")

    def test_orders_restart(self):
        Order.objects.create()
        Order.objects.create()
        with in_year(2031):
            self.assertEqual(OrderNumberSequence.take(), "ORD-2031-000001")

    def test_the_run_continues_within_a_year(self):
        """The reset is for the turn of the year and nothing else."""
        with in_year(2031):
            a = _next_payment_number(self.book, "collection")
            b = _next_payment_number(self.book, "collection")
            c = _next_payment_number(self.book, "collection")
        self.assertEqual([a, b, c],
                         ["COL-2031-000001", "COL-2031-000002", "COL-2031-000003"])


class TheAccountCodeIsNotYearly(TestCase):
    """ACC-088 has no year in it. Restarting that counter would mint a code
    the book already holds — the reset belongs only to numbers that carry
    the year they were issued in."""

    def test_it_carries_straight_on(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        settings = CurrentAccountSettings.for_book(book)
        first = settings.next_current_account_code()
        with in_year(2031):
            later = settings.next_current_account_code()
        self.assertEqual(first, "ACC-001")
        self.assertEqual(later, "ACC-002")


class TheDeployDoesNotRestartMidYear(TestCase):
    """The hazard the migration exists for.

    A counter partway through a year has no year recorded until the
    migration writes one. Read as "not this year", it would restart at 1 —
    and Laleli's invoice counter stands at 109, so the next invoice would
    be INV-2026-000001, a number already on a customer's paperwork, and
    the (book, series, number) constraint would refuse it.
    """

    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        # for_book CREATES the row; updating before it exists would match
        # nothing and quietly leave the defaults in place.
        self.settings = CurrentAccountSettings.for_book(self.book)

    def test_a_counter_stamped_with_this_year_carries_on(self):
        year = timezone.now().year
        CurrentAccountSettings.objects.filter(pk=self.settings.pk).update(
            next_invoice_seq=109, invoice_seq_year=year)
        settings = CurrentAccountSettings.for_book(self.book)
        self.assertEqual(settings.next_invoice_number(),
                         f"INV-{year}-000109")

    def test_an_unstamped_counter_is_what_the_migration_prevents(self):
        """Left null — the state the migration backfills — the very next
        number restarts the run. This is the failure, written down."""
        CurrentAccountSettings.objects.filter(pk=self.settings.pk).update(
            next_invoice_seq=109, invoice_seq_year=None)
        settings = CurrentAccountSettings.for_book(self.book)
        year = timezone.now().year
        self.assertEqual(settings.next_invoice_number(), f"INV-{year}-000001")


class TheMigrationStampsWhatIsRunning(TestCase):
    """Only counters that have issued something. One still at 1 has nothing
    to protect and starts cleanly whenever its first document is taken."""

    def test_it_leaves_an_untouched_counter_alone(self):
        import importlib
        from django.apps import apps
        # The module name starts with a digit, so it cannot be imported
        # with the import statement.
        migration = importlib.import_module(
            "accounting.migrations.0102_annual_number_reset")
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        fresh = CurrentAccountSettings.for_book(Book.objects.create(name="New"))
        busy = CurrentAccountSettings.for_book(Book.objects.create(name="Busy"))
        CurrentAccountSettings.objects.filter(pk=busy.pk).update(next_invoice_seq=109)

        migration.stamp_the_current_year(apps, None)

        fresh.refresh_from_db(); busy.refresh_from_db()
        self.assertIsNone(fresh.invoice_seq_year)
        self.assertEqual(busy.invoice_seq_year, timezone.now().year)
