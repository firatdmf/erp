"""A transfer between two cash accounts reaches the journal.

Run with:
    python manage.py test accounting.tests.test_cash_transfer_posting
"""
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from accounting.models import InTransfer
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import ensure_chart
from accounting.tests.test_current_account_transfer import TransferTestBase


class CashTransferPosting(TransferTestBase):
    """Cash and Bank does not move when money goes from the till to the
    bank, so the transfer was left out of the ledger — and the journal,
    which lists everything that happened, was missing one thing that did."""

    def setUp(self):
        super().setUp()
        ensure_chart()

    def _transfer(self, amount="250.00"):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url(), {
                "mode": "cash", "book": self.book.pk, "date": "2026-02-01",
                "from_cash_account": self.kasa.pk, "to_cash_account": self.banka.pk,
                "amount": amount, "currency": self.usd.pk,
            })
        return InTransfer.objects.get()

    def _entries(self, transfer):
        return JournalEntry.objects.filter(
            source_type=ContentType.objects.get_for_model(InTransfer), source_id=transfer.pk)

    def test_it_posts_one_entry_naming_both_cash_accounts(self):
        transfer = self._transfer()
        entry = self._entries(transfer).get()
        self.assertEqual(str(entry.date), "2026-02-01")
        lines = {("dr" if l.debit else "cr"): l for l in entry.lines.select_related("account")}
        self.assertEqual({l.account.code for l in lines.values()}, {"1000"})
        self.assertEqual(lines["dr"].cash_account, self.banka)     # where it went
        self.assertEqual(lines["cr"].cash_account, self.kasa)      # where it came from
        self.assertEqual(lines["dr"].debit, Decimal("250.00"))
        self.assertEqual(lines["cr"].credit, Decimal("250.00"))

    def test_it_shows_on_the_journal_page_and_opens_the_transfer(self):
        transfer = self._transfer()
        r = self.client.get(reverse("accounts:report_journal", args=[self.book.pk]), {"kind": "cash"})
        row = next(row for row in r.context["rows"] if row["entry"].source_id == transfer.pk)
        self.assertEqual(row["url"], reverse(
            "accounting:equity_transfer_detail",
            kwargs={"pk": self.book.pk, "source_pk": transfer.pk}))
        self.assertContains(r, "Transferred 250.00 USD from Ziraat to Garanti")

    def test_deleting_the_transfer_takes_its_entry_with_it(self):
        transfer = self._transfer()
        pk = transfer.pk
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("accounting:delete_equity_transfer",
                                     kwargs={"pk": self.book.pk, "source_pk": pk}))
        self.assertFalse(InTransfer.objects.filter(pk=pk).exists())
        self.assertFalse(JournalEntry.objects.filter(
            source_type=ContentType.objects.get_for_model(InTransfer), source_id=pk).exists())
