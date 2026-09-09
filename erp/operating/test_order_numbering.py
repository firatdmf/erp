"""Orders get a number, in the shape every other document here uses.

Orders were the one document with no reference of its own. `order_number`
existed but only web orders ever filled it, from a MAX+1 read taken
outside any lock, in a DK0000001 shape that matched nothing else. Every
one of the 41 orders in the database was null, which is why a printed
order could only name itself by database id.

They are numbered ORD-2026-000001 now — the same PREFIX-YEAR-NNNNNN the
business already issues:

    COL-2026-000101   collections
    PAY-2026-000099   payments
    INV-2026-000108   sales invoices
    PUR-2026-000105   purchase invoices

Only from now on. The orders that predate this stay null and go on being
named by id, because numbering them retroactively would hand a customer a
new reference for an order they already hold paperwork for.

Run with:
    python manage.py test operating.test_order_numbering
"""
import re
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from operating.models import Order, OrderNumberSequence

HOUSE_SHAPE = re.compile(r"^ORD-\d{4}-\d{6}$")


class ANewOrderIsNumbered(TestCase):
    def test_it_takes_the_house_shape(self):
        order = Order.objects.create()
        self.assertRegex(order.order_number, HOUSE_SHAPE)

    def test_the_year_is_this_year(self):
        order = Order.objects.create()
        self.assertEqual(order.order_number.split("-")[1],
                         str(timezone.now().year))

    def test_two_orders_never_share_a_number(self):
        numbers = [Order.objects.create().order_number for _ in range(5)]
        self.assertEqual(len(set(numbers)), 5)

    def test_the_sequence_counts_up(self):
        first = Order.objects.create().order_number
        second = Order.objects.create().order_number
        self.assertEqual(int(second.split("-")[2]), int(first.split("-")[2]) + 1)

    def test_a_number_given_by_hand_is_kept(self):
        """An import or a migration may carry the customer's own
        reference; the counter must not overwrite it."""
        order = Order.objects.create(order_number="DK0000270")
        self.assertEqual(order.order_number, "DK0000270")

    def test_the_year_is_stamped_not_counted(self):
        """The sequence runs straight on across the turn of the year, as
        the collection and invoice counters do. Resetting it would make
        ORD-2027-000001 the second order to carry that tail."""
        Order.objects.create()
        before = OrderNumberSequence.objects.get(pk=1).next_seq
        # Worked out BEFORE the patch: inside it, timezone.now() is the
        # mock, and .replace() on a MagicMock returns another MagicMock.
        in_2031 = timezone.now().replace(year=2031)
        # take() directly, not through an Order: patching timezone.now
        # globally would also reach the auto_now_add on created_at.
        with patch("django.utils.timezone.now", return_value=in_2031):
            later = OrderNumberSequence.take()
        self.assertTrue(later.startswith("ORD-2031-"))
        self.assertEqual(int(later.split("-")[2]), before)


class OlderOrdersAreLeftAlone(TestCase):
    """"Only the new ones from today." An order that predates the counter
    keeps its null and is named by id wherever it is printed."""

    def setUp(self):
        self.legacy = Order.objects.create()
        Order.objects.filter(pk=self.legacy.pk).update(order_number=None)
        self.legacy.refresh_from_db()

    def test_saving_one_does_not_number_it(self):
        self.legacy.notes = "edited"
        self.legacy.save()
        self.legacy.refresh_from_db()
        self.assertIsNone(self.legacy.order_number)

    def test_nor_does_updating_one_field(self):
        self.legacy.save(update_fields=["notes"])
        self.legacy.refresh_from_db()
        self.assertIsNone(self.legacy.order_number)


class TheCounterIsLocked(TransactionTestCase):
    """The generator this replaces read MAX and added one, outside any
    transaction. Two orders saved in the same instant read the same MAX,
    built the same number, and the second insert died on the unique
    constraint — a 500 on a save the user had every reason to expect to
    work. take() locks the row instead."""

    def test_concurrent_takes_do_not_collide(self):
        import threading
        numbers, errors = [], []

        def take():
            from django.db import connection
            try:
                numbers.append(OrderNumberSequence.take())
            except Exception as exc:      # pragma: no cover - shown on failure
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=take) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(numbers)), len(numbers),
                         f"the counter handed out a duplicate: {numbers}")


class TheStockLedgerStillRecognisesAnOrder(TestCase):
    """Stock movements reference an order by its number. The classifier
    that tells order movements from intake and adjustments matched the DK
    shape, so a movement written against ORD-2026-000001 would have
    dropped out of the order history it belongs to."""

    def test_both_shapes_are_recognised(self):
        from operating.views_warehouse import _ORDER_REF_RE
        for reference in ("ORD-2026-000001", "DK0000270"):
            self.assertRegex(reference, _ORDER_REF_RE)

    def test_a_supplier_barcode_is_not_mistaken_for_one(self):
        """The comment on that regex warns of exactly this: a "Deka"
        supplier mints DK-prefixed barcodes, and free-text reasons are
        not order references."""
        from operating.views_warehouse import _ORDER_REF_RE
        for reference in ("DK123", "ORDER-2026-000001", "ORD-000001"):
            self.assertNotRegex(reference, _ORDER_REF_RE)
