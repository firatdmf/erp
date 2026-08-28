# to run this test, use the command:
# python manage.py test accounting.test_cancelled_statement

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement, Payment


class CancelledStatementTests(TestCase):
    """?status=cancelled has to answer for documents, not just rows.

    A cancelled invoice leaves voided movements behind; a cancelled payment
    leaves none, because Payment.cancel deletes the movement outright rather
    than voiding it. The page asked one question and answered half of it,
    with nothing to say the other half existed.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="stmt", password="pw"
        )
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Kasa", currency=self.usd, balance=Decimal("1000.00"),
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="FIRAT", name="MUHAMMED FIRAT ÖZTÜRK",
            type="customer", default_currency=self.usd,
        )

    def _cancelled_payment(self, amount="180.59", when="2026-08-26"):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-2026-000075",
            type="collection", method="other", status="draft",
            date=when, amount=Decimal(amount), currency=self.usd,
        )
        payment.confirm()
        payment.cancel()
        return payment

    def _url(self, **params):
        url = reverse("accounts:statement", kwargs={"pk": self.cari.pk})
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return url

    def test_cancelling_a_payment_really_does_leave_no_row(self):
        """The premise. If this ever stops holding, the listing below is
        duplicating what the table already shows."""
        payment = self._cancelled_payment()

        self.assertEqual(payment.status, "cancelled")
        self.assertIsNone(payment.posted_movement_id)
        self.assertEqual(CariMovement.objects.filter(cari=self.cari).count(), 0)

    def test_the_cancelled_view_lists_the_payment(self):
        self._cancelled_payment()

        response = self.client.get(self._url(status="cancelled"))

        self.assertContains(response, "COL-2026-000075")
        self.assertContains(response, "180.59")

    def test_the_cancelled_view_says_so_when_there_is_nothing(self):
        response = self.client.get(self._url(status="cancelled"))

        self.assertContains(response, 'class="st-card st-cancelled')
        self.assertContains(response, "Nothing cancelled")

    def test_a_confirmed_payment_is_not_listed_as_cancelled(self):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-2026-000099",
            type="collection", method="cash", status="draft",
            date="2026-08-26", amount=Decimal("50.00"), currency=self.usd,
        )
        payment.confirm()

        response = self.client.get(self._url(status="cancelled"))

        self.assertNotContains(response, "COL-2026-000099")

    def test_the_normal_statement_does_not_list_cancelled_documents(self):
        """The default view is the live ledger — a cancelled document has no
        business appearing in it."""
        self._cancelled_payment()

        response = self.client.get(self._url())

        self.assertNotContains(response, "COL-2026-000075")
        # The section itself, not its wording — the page's stylesheet
        # mentions the phrase whatever the filter is.
        self.assertNotContains(response, 'class="st-card st-cancelled')

    def test_the_date_range_applies_to_the_documents_too(self):
        self._cancelled_payment(when="2026-08-26")

        inside = self.client.get(
            self._url(status="cancelled", date_from="2026-08-01", date_to="2026-08-31")
        )
        outside = self.client.get(
            self._url(status="cancelled", date_from="2026-09-01", date_to="2026-09-30")
        )

        self.assertContains(inside, "COL-2026-000075")
        self.assertNotContains(outside, "COL-2026-000075")
