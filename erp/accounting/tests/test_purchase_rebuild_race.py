"""Two rebuilds of one draft purchase at the same moment.

On 2026-11-12 PUR-2026-000115 went from 22 lines to 41. The ids told the
story: two rebuilds ran together, one starting a moment before the other,
their rows interleaved, and the later one's delete took only the first
three rows the earlier one had committed. The order-side mirror rebuilt the
purchase with no lock and no transaction, each row committed as it was
written, so the second rebuild could neither wait for the first nor see
what it was about to add.
"""
import threading
import time
from decimal import Decimal
from unittest import mock

from django.db import connection

from accounting.models import Book, CurrencyCategory, InvoiceItem
from accounting.models_accounts import CurrentAccount, Invoice
from accounting.views_purchase import rebuild_draft_items
from erp.testing import TransactionTestCase


def _lines(*names):
    return [{"description": name, "quantity": Decimal("10"), "unit": "piece",
             "unit_price": Decimal("2.00")} for name in names]


class TwoRebuildsAtOnce(TransactionTestCase):

    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        supplier = CurrentAccount.objects.create(
            book=book, code="C-OZC", name="Özce Tekstil", type="supplier", default_currency=usd)
        self.purchase = Invoice.objects.create(
            book=book, current_account=supplier, type="purchase", status="ordered",
            number="PUR-RACE", date="2026-09-18", due_date="2026-10-18", currency=usd)

    def test_the_purchase_ends_with_one_set_of_lines(self):
        """The first rebuild pauses after writing its first row; the second
        starts meanwhile. Whatever order they finish in, the purchase holds
        exactly one rebuild's lines — never a mix of both."""
        first_row_written = threading.Event()
        create = InvoiceItem.objects.create
        errors = []

        def slow_create(**kwargs):
            row = create(**kwargs)
            if threading.current_thread().name == "first" and kwargs["line_no"] == 1:
                first_row_written.set()
                time.sleep(0.5)        # the second rebuild starts in here
            return row

        def rebuild(lines):
            try:
                rebuild_draft_items(Invoice.objects.get(pk=self.purchase.pk), lines)
            except Exception as exc:   # pragma: no cover - shown on failure
                errors.append(exc)
            finally:
                connection.close()

        with mock.patch.object(InvoiceItem.objects, "create", side_effect=slow_create):
            first = threading.Thread(target=rebuild, name="first",
                                     args=(_lines("A1", "A2", "A3"),))
            second = threading.Thread(target=rebuild, name="second",
                                      args=(_lines("B1", "B2", "B3"),))
            first.start()
            self.assertTrue(first_row_written.wait(5))
            second.start()
            first.join()
            second.join()

        self.assertEqual(errors, [])
        rows = sorted(self.purchase.items.values_list("description", flat=True))
        self.assertIn(rows, (["A1", "A2", "A3"], ["B1", "B2", "B3"]),
                      f"both rebuilds left lines on the purchase: {rows}")
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.total, Decimal("60.00"))
