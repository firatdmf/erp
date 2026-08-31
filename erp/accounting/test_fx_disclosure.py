# to run this test, use the command:
# python manage.py test accounting.test_fx_disclosure

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CariAccount, CariMovement, CashAccount, CashTransactionEntry,
    CurrencyCategory, Payment,
)
from accounting.services_accounts import conversion_facts


class FxDisclosureBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="fx_tester", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric")
        # Object pages are refused unless the viewer is assigned the
        # row's book (accounting.book_scope.book_guarded).
        self.user.member.books.add(self.book)
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-078", name="RANA UYGUR",
            default_currency=self.try_)

    def payment(self, currency, rate=Decimal("0.020800"), confirm=True):
        p = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-FX-%s" % currency.code,
            type="collection", method="cash", status="draft",
            date="2026-08-17", amount=Decimal("200.00"),
            currency=currency, exchange_rate=rate)
        if confirm:
            p.confirm()
        return p


class ConversionFactsTest(FxDisclosureBase):
    """One definition of "what did this convert at", so every page states
    the same thing."""

    def test_a_base_currency_record_has_nothing_to_state(self):
        """A rate of 1 beside a repeated figure tells the reader nothing."""
        self.assertIsNone(conversion_facts(self.payment(self.usd)))

    def test_a_foreign_payment_reports_its_rate_and_base_value(self):
        fx = conversion_facts(self.payment(self.try_))
        self.assertEqual(fx["rate"], Decimal("0.020800"))
        self.assertEqual(fx["base_amount"], Decimal("-4.16"))
        self.assertEqual(fx["base_code"], "USD")
        self.assertFalse(fx["pending"])

    def test_the_figures_come_from_the_ledger_row_not_the_document(self):
        """The row is what actually moved the balance. A rate corrected on
        a confirmed document reaches the balance only on resync, and until
        then the page must show what the ledger holds."""
        p = self.payment(self.try_)
        p.exchange_rate = Decimal("0.030000")
        p.save(update_fields=["exchange_rate"])

        fx = conversion_facts(p)
        self.assertEqual(fx["rate"], Decimal("0.020800"))

        p.resync_posted_movement()
        p.refresh_from_db()
        self.assertEqual(conversion_facts(p)["rate"], Decimal("0.030000"))

    def test_an_unposted_document_is_marked_as_a_projection(self):
        fx = conversion_facts(self.payment(self.try_, confirm=False))
        self.assertTrue(fx["pending"])
        self.assertEqual(fx["rate"], Decimal("0.020800"))
        self.assertEqual(fx["base_amount"], Decimal("4.16"))

    def test_a_movement_reports_its_own_figures(self):
        mv = CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-08-17",
            amount=Decimal("200.00"), currency=self.try_,
            movement_type="adjustment", exchange_rate=Decimal("0.020800"),
            amount_base=Decimal("4.16"))
        fx = conversion_facts(mv)
        self.assertEqual(fx["rate"], Decimal("0.020800"))
        self.assertEqual(fx["base_amount"], Decimal("4.16"))

    def test_a_cash_entry_reports_its_own_figures(self):
        account = CashAccount.objects.create(
            book=self.book, name="Ziraat", currency=self.try_,
            balance=Decimal("0.00"))
        p = self.payment(self.try_, confirm=False)
        p.cash_account = account
        p.save()
        p.confirm()
        entry = CashTransactionEntry.objects.filter(cash_account=account).first()
        self.assertIsNotNone(entry)
        fx = conversion_facts(entry)
        self.assertEqual(fx["rate"], Decimal("0.020800"))
        self.assertEqual(fx["base_amount"], entry.amount_in_base_currency)

    def test_none_is_handled(self):
        self.assertIsNone(conversion_facts(None))


class PaymentDetailPageTest(FxDisclosureBase):

    def url(self, payment):
        return reverse("accounts:payment_detail", kwargs={"pk": payment.pk})

    def test_a_foreign_payment_page_states_the_rate_and_the_base_value(self):
        p = self.payment(self.try_)
        response = self.client.get(self.url(p))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exchange Rate")
        # format_rate drops trailing zeros on purpose — 0.0208, not
        # 0.020800 — while never going below two decimals.
        self.assertContains(response, "0.0208")
        self.assertContains(response, "1 TRY = 0.0208 USD")
        self.assertContains(response, "Value in USD")
        self.assertContains(response, "4.16")

    def test_a_base_currency_payment_page_says_nothing_about_rates(self):
        """Every other payment in the book is in USD — a rate row on all
        of them would be noise on 66 pages to serve one."""
        p = self.payment(self.usd)
        response = self.client.get(self.url(p))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Exchange Rate")
        self.assertNotContains(response, "Value in USD")


class StatementRowTest(FxDisclosureBase):
    """The debit/credit figure is in the movement's own currency while the
    running balance beside it is a base-currency sum. Without the
    conversion stated, a lira row reads 200.00 against a balance that
    moved by 4.16 and nothing on the page connects them."""

    def url(self):
        return reverse("accounts:statement", kwargs={"pk": self.cari.pk})

    def test_a_foreign_row_states_what_it_came_to(self):
        self.payment(self.try_)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="st-fx">')
        self.assertContains(response, "TRY ·")
        self.assertContains(response, "4.16")
        self.assertContains(response, "@ 0.0208")

    def test_a_base_currency_row_says_nothing(self):
        self.payment(self.usd)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        # The class name also appears in the stylesheet, so assert on the
        # rendered span rather than the bare word.
        self.assertNotContains(response, '<span class="st-fx">')

    def test_a_base_currency_row_costs_no_query_to_dismiss(self):
        """conversion_facts returns before touching the database for a row
        already in base currency — otherwise a 200-row statement would pay
        200 lookups to display nothing. (The rows the statement does spend
        queries on are _attach_links fetching each row's document, which
        predates this.)"""
        mv = CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-08-17",
            amount=Decimal("10.00"), currency=self.usd,
            movement_type="adjustment")
        mv = CariMovement.objects.select_related("currency").get(pk=mv.pk)
        with self.assertNumQueries(0):
            self.assertIsNone(conversion_facts(mv))

    def test_a_foreign_row_costs_one(self):
        mv = CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-08-17",
            amount=Decimal("200.00"), currency=self.try_,
            movement_type="adjustment", exchange_rate=Decimal("0.0208"),
            amount_base=Decimal("4.16"))
        mv = CariMovement.objects.select_related("currency").get(pk=mv.pk)
        with self.assertNumQueries(1):
            self.assertIsNotNone(conversion_facts(mv))
