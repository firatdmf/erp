"""A payment taken at a typed rate records the gap to the published one.

The account settles at the typed rate, the kasa carries the money at what
it was worth, and 5900 takes the difference — at confirmation, on its
own, with the person told what it came to.

Run with:
    python manage.py test accounting.tests.test_realised_fx
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounting import services
from accounting.models import (
    Book, CashAccount, CashTransactionEntry, CurrencyCategory, CurrencyExchangeRate, Payment,
)
from accounting.models_accounts import CurrentAccount
from accounting.models_ledger import JournalEntry, JournalLine
from accounting.services_fx import book_realised_fx
from accounting.services_ledger import ensure_chart


class _Base(TestCase):
    """Nick Greece: a dollar account paid in euros, in a dollar book."""

    DAY = date(2026, 9, 24)

    def setUp(self):
        services._RATE_MEMO.clear()
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        ensure_chart()
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-094", name="Nick Greece", type="customer",
            default_currency=self.usd)
        self.box = CashAccount.objects.create(
            book=self.book, name="Cash EUR", currency=self.eur, balance=Decimal("2000.00"))
        CurrencyExchangeRate.objects.create(
            from_currency="EUR", to_currency="USD", rate=Decimal("1.141100"), date=self.DAY)
        user = get_user_model().objects.create_user("nick", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.user = user
        self.client.force_login(user)

    def _payment(self, type_, amount, rate, *, currency=None, day=None, confirm=True):
        payment = Payment(
            current_account=self.account, book=self.book,
            number=f"P-{Payment.objects.count() + 1}", type=type_, method="cash",
            status="draft", date=day or self.DAY, amount=Decimal(amount),
            currency=currency or self.eur, cash_account=self.box)
        payment.set_stated_rate(Decimal(rate) if rate is not None else None)
        payment.save()
        if confirm:
            payment.confirm()
        return payment

    def _lines(self, payment):
        entry = JournalEntry.objects.get(source_id=payment.posted_movement_id)
        return {(l.account.code, "dr" if l.debit else "cr"): (l.debit or l.credit)
                for l in entry.lines.all()}


class TheGapReachesFiveNineHundred(_Base):
    def test_a_refund_worth_more_than_it_settles_is_a_loss(self):
        # €201 refunded at 1.126368 clears exactly $226.40 — but €201 was
        # worth $229.36 that day. The $2.96 is money the book gave away.
        payment = self._payment("refund_in", "201.00", "1.126368")
        self.assertEqual(payment.published_rate, Decimal("1.141100"))
        fx = payment.realised_fx()
        self.assertEqual(fx["base_stated"], Decimal("226.40"))
        self.assertEqual(fx["base_published"], Decimal("229.36"))
        self.assertEqual(fx["difference"], Decimal("-2.96"))
        self.assertEqual(self._lines(payment), {
            ("1200", "dr"): Decimal("226.40"),
            ("1000", "cr"): Decimal("229.36"),
            ("5900", "dr"): Decimal("2.96"),
        })

    def test_a_collection_worth_more_than_it_settles_is_a_gain(self):
        # €350 at 1.128571 clears a $395.00 sale; the euros were worth $399.38
        # (399.385, rounded half-even like every row in the ledger).
        payment = self._payment("collection", "350.00", "1.128571")
        self.assertEqual(payment.realised_fx()["difference"], Decimal("4.38"))
        self.assertEqual(self._lines(payment), {
            ("1200", "cr"): Decimal("395.00"),
            ("1000", "dr"): Decimal("399.38"),
            ("5900", "cr"): Decimal("4.38"),
        })
        # The account moved by what the rate settled, to the cent.
        self.account.refresh_from_db()
        self.assertEqual(self.account.cached_balance, Decimal("-395.00"))

    def test_the_kasa_carries_the_money_at_what_it_was_worth(self):
        payment = self._payment("collection", "350.00", "1.128571")
        entry = CashTransactionEntry.objects.get(content_pk=payment.pk)
        self.assertEqual(entry.amount, Decimal("350.00"))
        self.assertEqual(entry.exchange_rate, Decimal("1.141100"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("399.38"))

    def test_the_published_rate_left_alone_records_nothing(self):
        payment = self._payment("collection", "350.00", "1.141100")
        self.assertEqual(payment.published_rate, Decimal("1.141100"))
        self.assertEqual(payment.realised_fx()["difference"], Decimal("0.00"))
        self.assertEqual(self._lines(payment), {
            ("1200", "cr"): Decimal("399.38"),
            ("1000", "dr"): Decimal("399.38"),
        })
        self.assertFalse(JournalLine.objects.filter(account__code="5900").exists())

    def test_no_typed_rate_means_nothing_to_compare(self):
        payment = self._payment("collection", "350.00", None)
        self.assertIsNone(payment.published_rate)
        self.assertIsNone(payment.realised_fx())
        self.assertFalse(JournalLine.objects.filter(account__code="5900").exists())

    def test_a_payment_in_the_books_own_currency_has_no_rate_to_hold(self):
        payment = self._payment("collection", "100.00", "1.000000", currency=self.usd)
        self.assertIsNone(payment.published_rate)
        self.assertIsNone(payment.realised_fx())

    def test_editing_the_rate_re_records_the_difference_once(self):
        payment = self._payment("refund_in", "201.00", "1.126368")
        payment.set_stated_rate(Decimal("1.150000"))
        payment.save()
        payment.sync_cash_entry()
        payment.resync_posted_movement()
        # 201 × 1.15 = 231.15 settled; worth 229.36 → gave away less: a gain of 1.79.
        self.assertEqual(JournalEntry.objects.filter(source_id=payment.posted_movement_id).count(), 1)
        self.assertEqual(self._lines(payment), {
            ("1200", "dr"): Decimal("231.15"),
            ("1000", "cr"): Decimal("229.36"),
            ("5900", "cr"): Decimal("1.79"),
        })
        entry = CashTransactionEntry.objects.get(content_pk=payment.pk)
        self.assertEqual(entry.amount_in_base_currency, Decimal("229.36"))

    def test_the_entry_balances_either_way(self):
        for type_, rate in (("refund_in", "1.126368"), ("collection", "1.128571"),
                            ("payment", "1.200000"), ("refund_out", "1.100000")):
            payment = self._payment(type_, "201.00", rate)
            lines = JournalLine.objects.filter(entry__source_id=payment.posted_movement_id)
            debits = sum(l.debit for l in lines)
            credits = sum(l.credit for l in lines)
            self.assertEqual(debits, credits, type_)
            self.assertEqual(lines.count(), 3, type_)


class ThePersonIsTold(_Base):
    def test_the_form_says_what_the_typed_rate_cost(self):
        response = self.client.post(
            reverse("accounts:payment_create", kwargs={"book_id": self.book.pk}), {
                "account": self.account.pk, "type": "refund_in", "method": "cash",
                "date": "2026-09-24", "amount": "201.00", "currency": self.eur.pk,
                "cash_account": self.box.pk, "exchange_rate": "1.126368", "auto_confirm": "1",
            }, follow=True)
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        said = [t for t in texts if "Exchange rate loss of USD 2.96" in t]
        self.assertEqual(len(said), 1, texts)
        self.assertIn("published rate 1.1411 ", said[0])
        self.assertIn("your rate 1.126368", said[0])
        self.assertIn(reverse("accounts:fx_report", kwargs={"book_id": self.book.pk}), said[0])

    def test_nothing_is_said_at_the_published_rate(self):
        response = self.client.post(
            reverse("accounts:payment_create", kwargs={"book_id": self.book.pk}), {
                "account": self.account.pk, "type": "collection", "method": "cash",
                "date": "2026-09-24", "amount": "350.00", "currency": self.eur.pk,
                "cash_account": self.box.pk, "exchange_rate": "1.141100", "auto_confirm": "1",
            }, follow=True)
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertFalse([t for t in texts if "Exchange rate" in t], texts)

    def test_the_report_lists_each_difference_and_the_total(self):
        self._payment("refund_in", "201.00", "1.126368")    # −2.96
        self._payment("collection", "350.00", "1.128571")   # +4.38
        self._payment("collection", "405.00", "1.141100")   #  0.00, not listed
        realised = book_realised_fx(self.book)
        self.assertEqual([r["fx"]["difference"] for r in realised["rows"]],
                         [Decimal("4.38"), Decimal("-2.96")])
        self.assertEqual(realised["total"], Decimal("1.42"))

        response = self.client.get(reverse("accounts:fx_report", kwargs={"book_id": self.book.pk}))
        self.assertEqual(response.status_code, 200)
        page = response.content.decode()
        self.assertIn("Differences from typed rates", page)
        self.assertIn("P-1", page)
        self.assertIn("P-2", page)
        self.assertNotIn("P-3", page)
        self.assertIn("+1.42", page)


class TheBackfill(_Base):
    def test_old_payments_are_given_their_rate_and_re_posted(self):
        from io import StringIO
        from django.core.management import call_command

        payment = self._payment("refund_in", "201.00", "1.126368")
        # As a payment confirmed before the snapshot existed: no photograph,
        # a two-line entry, a kasa row at the typed rate.
        Payment.objects.filter(pk=payment.pk).update(published_rate=None)
        payment.refresh_from_db()
        from accounting.services_posting import post_movement
        post_movement(payment.posted_movement)
        payment.sync_cash_entry()
        self.assertEqual(len(self._lines(payment)), 2)
        self.assertEqual(CashTransactionEntry.objects.get(content_pk=payment.pk).amount_in_base_currency,
                         Decimal("226.40"))

        out = StringIO()
        call_command("backfill_realised_fx", stdout=out)
        payment.refresh_from_db()
        self.assertIsNone(payment.published_rate, "a dry run writes nothing")
        self.assertIn("would record", out.getvalue())

        call_command("backfill_realised_fx", "--apply", stdout=out)
        payment.refresh_from_db()
        self.assertEqual(payment.published_rate, Decimal("1.141100"))
        self.assertEqual(self._lines(payment)[("5900", "dr")], Decimal("2.96"))
        self.assertEqual(CashTransactionEntry.objects.get(content_pk=payment.pk).amount_in_base_currency,
                         Decimal("229.36"))
        # Idempotent: photographed once, skipped after.
        out = StringIO()
        call_command("backfill_realised_fx", "--apply", stdout=out)
        self.assertIn("0 payment(s) recorded", out.getvalue())
