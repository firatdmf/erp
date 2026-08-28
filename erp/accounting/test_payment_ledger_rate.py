# to run this test, use the command:
# python manage.py test accounting.test_payment_ledger_rate

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import (
    Book,
    CariAccount,
    CariMovement,
    CurrencyCategory,
    Invoice,
    Payment,
)


class LedgerRateTestBase(TestCase):
    """The rate typed on a document must be the rate its ledger row
    converts at. It reached the cash ledger and stopped there: the cari
    movement went on using the published rate, so the figure the operator
    corrected was not the figure their balance moved by."""

    ENTERED = Decimal("0.020800")

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="rate_tester", password="pw"
        )
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-078", name="RANA UYGUR",
            default_currency=self.try_,
        )

    def make_payment(self, rate, amount="200.00", currency=None):
        return Payment.objects.create(
            cari=self.cari, book=self.book,
            number="COL-TEST-%s" % (rate or "none"),
            type="collection", method="cash", status="draft",
            date="2026-08-17",
            amount=Decimal(amount),
            currency=currency or self.try_,
            exchange_rate=rate,
        )


class PaymentLedgerRateTest(LedgerRateTestBase):

    def test_the_entered_rate_is_what_the_movement_converts_at(self):
        payment = self.make_payment(self.ENTERED)
        movement = payment.confirm()

        self.assertEqual(movement.exchange_rate, self.ENTERED)
        # 200 TRY at 0.0208 is 4.16 USD, and a collection is negative.
        self.assertEqual(movement.amount_base, Decimal("-4.16"))

    def test_the_entered_rate_is_what_the_balance_moves_by(self):
        """The movement carrying the rate is only half of it — the
        balance is a sum of amount_base, and that is what people read."""
        payment = self.make_payment(self.ENTERED)
        payment.confirm()

        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("-4.16"))

    def test_no_rate_typed_still_uses_the_published_one(self):
        """Null means nobody said, not "one to one" — the whole reason
        the field is nullable."""
        payment = self.make_payment(None)
        movement = payment.confirm()

        self.assertNotEqual(movement.exchange_rate, Decimal("1.000000"))
        self.assertNotEqual(movement.amount_base, Decimal("-200.00"))

    def test_editing_the_rate_moves_the_balance_with_it(self):
        payment = self.make_payment(self.ENTERED)
        payment.confirm()

        payment.exchange_rate = Decimal("0.030000")
        payment.save(update_fields=["exchange_rate"])
        payment.resync_posted_movement()

        payment.posted_movement.refresh_from_db()
        self.assertEqual(payment.posted_movement.exchange_rate, Decimal("0.030000"))
        self.assertEqual(payment.posted_movement.amount_base, Decimal("-6.00"))
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("-6.00"))

    def test_a_base_currency_payment_ignores_a_stray_rate(self):
        """Nothing to convert — a rate left behind by a currency switch
        must not scale the figure."""
        payment = self.make_payment(self.ENTERED, currency=self.usd)
        movement = payment.confirm()

        self.assertEqual(movement.exchange_rate, Decimal("1.000000"))
        self.assertEqual(movement.amount_base, Decimal("-200.00"))


class InvoiceRateIsNotConsultedTest(LedgerRateTestBase):
    """Invoice.exchange_rate defaults to 1.000000 and no view sets it, so
    a default cannot be told apart from a deliberate entry. Reading it
    would convert every foreign-currency invoice at par — which is why
    the source is asked through an opt-in method rather than by looking
    for an exchange_rate field."""

    def test_an_invoice_does_not_opt_in(self):
        self.assertFalse(hasattr(Invoice, "ledger_exchange_rate"))

    def test_a_foreign_currency_invoice_row_still_uses_the_published_rate(self):
        from django.contrib.contenttypes.models import ContentType

        invoice = Invoice.objects.create(
            cari=self.cari, book=self.book, number="INV-TEST-1",
            type="sale", status="draft", date="2026-08-17",
            due_date="2026-09-17", currency=self.try_,
        )
        self.assertEqual(invoice.exchange_rate, Decimal("1.000000"))

        movement = CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-08-17",
            amount=Decimal("200.00"), currency=self.try_,
            movement_type="invoice_sale",
            source_type=ContentType.objects.get_for_model(Invoice),
            source_id=invoice.pk,
        )

        self.assertNotEqual(movement.exchange_rate, Decimal("1.000000"))
        self.assertNotEqual(movement.amount_base, Decimal("200.00"))

    def test_a_movement_with_no_source_is_unaffected(self):
        movement = CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-08-17",
            amount=Decimal("200.00"), currency=self.try_,
            movement_type="adjustment",
        )
        self.assertIsNone(movement.entered_rate())
        self.assertNotEqual(movement.exchange_rate, Decimal("1.000000"))
