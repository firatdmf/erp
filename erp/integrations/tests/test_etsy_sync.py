# to run this test, use the command:
# python manage.py test integrations.tests.test_etsy_sync
import copy
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from accounting.models import EquityDivident, EquityExpense, ExpenseCategory
from accounting.models_accounts import CurrentAccountMovement
from crm.models import Company
from integrations import etsy_api, etsy_sync
from integrations.models import EtsyLedgerEntry, EtsyReceipt
from integrations.tests.test_etsy import LEDGER, RECEIPT, EtsyBase, _money
from marketing.models import Product, ProductVariant
from operating.models import Order, WarehouseProduct

START = datetime(2026, 10, 1, tzinfo=dt_timezone.utc)


def _receipt(**changes):
    r = copy.deepcopy(RECEIPT)
    r.update(changes)
    return r


class SyncBase(EtsyBase):
    def setUp(self):
        super().setUp()
        self.company = Company.objects.create(name="Etsy")
        self.etsy.company = self.company
        self.etsy.save()
        variant = ProductVariant.objects.create(
            product=Product.objects.create(title="Weave", sku="RK12471"), variant_sku="RK12471.GW9")
        WarehouseProduct.objects.create(warehouse=self.shop, name="Weave", sku="RK12471.GW9",
                                        catalog_variant=variant)
        self.fees = ExpenseCategory.objects.create(name="Comissions and Fees")
        self.connection = self.connected(
            warehouse=self.shop, current_account=self.etsy, fee_category=self.fees,
            payout_member=self.admin.member, sync_from=START, connected_by=self.admin)

    def run_sync(self, receipts=(), entries=()):
        with mock.patch.object(etsy_api.EtsyClient, "receipts", return_value=list(receipts)), \
                mock.patch.object(etsy_api.EtsyClient, "ledger_entries", return_value=list(entries)):
            return etsy_sync.sync(self.connection)


class OrdersArriveAsDrafts(SyncBase):
    def test_an_etsy_order_becomes_a_draft_order_to_etsy(self):
        self.run_sync(receipts=[RECEIPT])
        order = Order.objects.get()
        self.assertEqual((order.company, order.current_account), (self.company, self.etsy))
        self.assertEqual(order.order_status, "pending")
        self.assertIn("#4197103539", order.notes)
        self.assertIn("Tyche Gage", order.notes)
        [line] = order.items.all()
        self.assertEqual((line.product_variant.variant_sku, line.quantity, line.price),
                         ("RK12471.GW9", Decimal("1"), Decimal("99.99")))
        self.assertEqual([(a.label, a.amount) for a in order.adjustments.all()],
                         [("Etsy discount", Decimal("-15.00"))])
        self.assertEqual(order.billable_value(), Decimal("84.99"))
        record = EtsyReceipt.objects.get()
        self.assertEqual((record.state, record.order, record.problem), ("recorded", order, ""))
        # An open order is no sale: nothing reaches Etsy's account until it is completed.
        self.assertFalse(CurrentAccountMovement.objects.filter(movement_type="order_sale").exists())

    def test_running_again_records_nothing_twice(self):
        self.run_sync(receipts=[RECEIPT], entries=LEDGER)
        self.run_sync(receipts=[RECEIPT], entries=LEDGER)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(EquityExpense.objects.count(), 2)
        self.assertEqual(EquityDivident.objects.count(), 1)

    def test_a_sku_not_on_the_shelf_waits_for_a_person(self):
        r = _receipt()
        r["transactions"][0]["sku"] = "RK12471GW9"
        recorded, waiting = self.run_sync(receipts=[r])
        self.assertFalse(Order.objects.exists())
        record = EtsyReceipt.objects.get()
        self.assertEqual(record.state, "needs_person")
        self.assertIn("RK12471GW9", record.problem)
        self.assertEqual((recorded, waiting), (0, 1))

    def test_a_refund_waits_and_a_cancellation_is_skipped(self):
        self.run_sync(receipts=[_receipt(receipt_id=1, status="Fully Refunded"),
                                _receipt(receipt_id=2, status="Canceled")])
        self.assertFalse(Order.objects.exists())
        self.assertEqual(dict(EtsyReceipt.objects.values_list("receipt_id", "state")),
                         {1: "needs_person", 2: "skipped"})

    def test_shipping_is_billed_and_a_mismatch_is_said(self):
        r = _receipt(total_shipping_cost=_money(500), discount_amt=_money(0), subtotal=_money(9000))
        self.run_sync(receipts=[r])
        order = Order.objects.get()
        self.assertEqual([(a.label, a.amount) for a in order.adjustments.all()],
                         [("Shipping", Decimal("5.00"))])
        record = EtsyReceipt.objects.get()
        self.assertIn("95.00", record.problem)      # Etsy says 90.00 + 5.00; the order bills 104.99

    def test_what_came_before_the_sync_was_switched_on_is_left_alone(self):
        self.connection.sync_from = timezone.now()
        self.connection.save()
        self.run_sync(receipts=[RECEIPT], entries=LEDGER)
        self.assertFalse(EtsyReceipt.objects.exists())
        self.assertFalse(EtsyLedgerEntry.objects.exists())

    def test_a_switched_off_sync_asks_etsy_nothing(self):
        self.connection.sync_from = None
        self.connection.save()
        with mock.patch.object(etsy_api.EtsyClient, "receipts") as receipts:
            etsy_sync.sync(self.connection)
        receipts.assert_not_called()


class LedgerEntriesAreRecorded(SyncBase):
    def test_fees_are_expenses_paid_by_etsy(self):
        self.run_sync(entries=LEDGER)
        expenses = EquityExpense.objects.order_by("amount")
        self.assertEqual([e.amount for e in expenses], [Decimal("0.20"), Decimal("8.59")])
        for e in expenses:
            self.assertEqual((e.category, e.paid_by_current_account, e.cash_account_id),
                             (self.fees, self.etsy, None))
            self.assertEqual(e.date, timezone.localtime(
                datetime.fromtimestamp(1791590402, tz=dt_timezone.utc)).date())

    def test_a_payout_is_a_dividend_to_the_chosen_stakeholder(self):
        self.run_sync(entries=LEDGER)
        dividend = EquityDivident.objects.get()
        self.assertEqual((dividend.amount, dividend.member, dividend.paid_by_current_account),
                         (Decimal("76.20"), self.admin.member, self.etsy))

    def test_the_buyers_payment_and_its_tax_are_covered_by_the_order(self):
        self.run_sync(entries=LEDGER)
        states = dict(EtsyLedgerEntry.objects.values_list("entry_id", "state"))
        self.assertEqual(states, {1: "covered", 2: "covered", 3: "recorded", 4: "recorded",
                                  5: "recorded"})
        # Fees and the payout take Etsy's account down by what they are.
        self.etsy.refresh_from_db()
        self.assertEqual(self.etsy.recompute_balance(save=False), Decimal("-84.99"))

    def test_money_that_is_not_a_payment_waits_for_a_person(self):
        card = {"entry_id": 9, "created_timestamp": 1791590400, "ledger_type": "billing_payment",
                "reference_type": "billing_payment", "amount": 20, "balance": 0}
        refund = {"entry_id": 10, "created_timestamp": 1791590401, "ledger_type": "REFUND_GROSS",
                  "reference_type": "shop_payment", "amount": -5000, "balance": -5000}
        dollars = {"entry_id": 11, "created_timestamp": 1791590402, "ledger_type": "transaction",
                   "reference_type": "transaction", "amount": -100, "balance": 0, "currency": "EUR"}
        recorded, waiting = self.run_sync(entries=[card, refund, dollars])
        self.assertEqual(waiting, 3)
        self.assertFalse(EquityExpense.objects.exists())
        self.assertIn("refund", EtsyLedgerEntry.objects.get(entry_id=10).problem.lower())
        self.assertIn("EUR", EtsyLedgerEntry.objects.get(entry_id=11).problem)


class ThePage(SyncBase):
    def test_the_sync_starts_only_with_every_setting_chosen(self):
        self.connection.sync_from = None
        self.connection.fee_category = None
        self.connection.save()
        self.client.post(reverse("integrations:etsy_sync_start", args=[self.book.pk]))
        self.connection.refresh_from_db()
        self.assertIsNone(self.connection.sync_from)
        self.connection.fee_category = self.fees
        self.connection.save()
        self.client.post(reverse("integrations:etsy_sync_start", args=[self.book.pk]))
        self.connection.refresh_from_db()
        self.assertIsNotNone(self.connection.sync_from)

    def test_sync_now_runs_and_says_what_it_did(self):
        with mock.patch.object(etsy_api.EtsyClient, "receipts", return_value=[RECEIPT]), \
                mock.patch.object(etsy_api.EtsyClient, "ledger_entries", return_value=LEDGER):
            r = self.client.post(reverse("integrations:etsy_sync_now", args=[self.book.pk]), follow=True)
        self.assertContains(r, "Synced: 6 recorded, 0 waiting for a person.")
        self.connection.refresh_from_db()
        self.assertIsNotNone(self.connection.last_synced_at)

    def test_the_balance_check_counts_open_etsy_orders_as_the_only_gap(self):
        self.run_sync(receipts=[RECEIPT], entries=LEDGER)
        r = self.client.get(reverse("integrations:etsy_book", args=[self.book.pk]))
        sync = r.context["sync"]
        # Etsy: 0.00 after paying out. Books: −84.99 (fees and payout, no sale
        # yet). The open order is the 84.99 between them.
        self.assertEqual((sync["etsy_balance"], sync["erp_balance"], sync["open_total"]),
                         (Decimal("0.00"), Decimal("-84.99"), Decimal("84.99")))
        self.assertEqual(sync["gap"], Decimal("0.00"))

    def test_a_waiting_item_can_be_marked_handled(self):
        r = _receipt()
        r["transactions"][0]["sku"] = "NOPE"
        self.run_sync(receipts=[r])
        record = EtsyReceipt.objects.get()
        self.client.post(reverse("integrations:etsy_mark_handled",
                                 args=[self.book.pk, "receipt", record.pk]))
        record.refresh_from_db()
        self.assertEqual(record.state, "handled")


class NowAndThen(SyncBase):
    def test_it_runs_at_most_once_an_hour(self):
        cache.delete("etsy-sync")
        with mock.patch.object(etsy_sync, "sync_all") as sync_all, \
                self.captureOnCommitCallbacks(execute=True):
            etsy_sync.sync_now_and_then()
            etsy_sync.sync_now_and_then()
        # The work runs on a thread; give it a moment, then count the starts.
        import time
        time.sleep(0.2)
        self.assertEqual(sync_all.call_count, 1)
        cache.delete("etsy-sync")

    def test_a_failing_run_is_kept_on_the_connection(self):
        with mock.patch.object(etsy_api.EtsyClient, "receipts", side_effect=etsy_api.EtsyError("Etsy is down")):
            etsy_sync.sync_all()
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.last_sync_error, "Etsy is down")
