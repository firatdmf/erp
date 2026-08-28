# to run this test, use the command:
# python manage.py test accounting.test_statement_balance_invariant

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CariAccount, CariMovement, CurrencyCategory, Payment,
)


class StatementBalanceInvariantTest(TestCase):
    """An account page and its statement must never print different
    numbers for the same account.

    They used to be computed differently — the account page summed EVERY
    movement, the statement re-derived which rows were halves of cancelled
    pairs and dropped them — so they agreed only while the dropped set
    happened to sum to zero. A hard-deleted payment broke that and the two
    pages disagreed by 150.00.

    Both now sum CariMovementQuerySet.live(). These tests assert the
    property that replaced the coincidence: whatever is voided, the two
    numbers are the same number, because there is only one rule.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="invariant_tester", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.cari = CariAccount.objects.create(
            book=self.book, code="PERAKENDE", name="Perakende Satışları",
            default_currency=self.usd)

    # -- helpers ---------------------------------------------------------
    def collection(self, number, amount):
        p = Payment.objects.create(
            cari=self.cari, book=self.book, number=number,
            type="collection", method="cash", status="draft",
            date="2026-07-10", amount=Decimal(amount), currency=self.usd)
        p.confirm()
        return p

    def sale(self, amount):
        return CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-07-10",
            amount=Decimal(amount), currency=self.usd,
            movement_type="order_sale")

    def assert_agrees(self):
        """The account page and the statement, from the one rule."""
        self.cari.refresh_from_db()
        ledger = (self.cari.movements.live()
                  .aggregate(s=Sum("amount_base"))["s"] or Decimal("0.00"))
        self.assertEqual(
            ledger, self.cari.cached_balance,
            "cached_balance must equal the sum of live movements")
        self.assertEqual(
            self.statement_closing(), self.cari.cached_balance,
            "statement closing must equal the account balance")
        return ledger

    def statement_closing(self):
        response = self.client.get(
            reverse("accounts:statement", kwargs={"pk": self.cari.pk}))
        self.assertEqual(response.status_code, 200)
        return response.context["closing"]

    # -- scenarios -------------------------------------------------------
    def test_a_plain_account_agrees(self):
        self.sale("57.01")
        self.collection("COL-1", "57.01")
        self.assert_agrees()
        self.assertEqual(self.statement_closing(), Decimal("0.00"))

    def test_a_cancelled_payment_agrees(self):
        self.sale("150.00")
        p = self.collection("COL-2", "150.00")
        p.cancel(reason="test")
        self.assert_agrees()
        self.assertEqual(self.statement_closing(), Decimal("150.00"))

    def test_a_DELETED_payment_agrees(self):
        """The PERAKENDE case. A payment removed outright leaves its rows
        orphaned: the CANCEL half is matched on reference text, which
        survives, while its partner was matched on the document's status,
        which no longer exists. Hiding one half of a zero-sum pair made
        the statement close 150.00 below the account page.
        """
        self.sale("150.00")
        p = self.collection("TAH-2026-000022", "150.00")

        # The historical shape: a cancel counter-row exists, and then the
        # payment row itself is deleted rather than cancelled.
        CariMovement.objects.create(
            cari=self.cari, book=self.book, date="2026-07-10",
            amount=Decimal("150.00"), currency=self.usd,
            movement_type="adjustment",
            reference="CANCEL TAH-2026-000022",
            description="CANCEL — Collection (from customer)",
            source_type=p.posted_movement.source_type,
            source_id=p.pk,
        )
        payment_pk = p.pk
        Payment.objects.filter(pk=payment_pk).delete()

        self.assertFalse(Payment.objects.filter(pk=payment_pk).exists())
        self.assert_agrees()
        self.assertEqual(self.statement_closing(), Decimal("150.00"))

    def test_voiding_a_row_moves_both_numbers_together(self):
        """The property that replaced the coincidence.

        Voiding is no longer something a page decides while rendering; it
        is a fact on the row that the balance and the statement both read.
        So voiding anything at all must move the two numbers in lockstep —
        there is no longer a way for one to see a row the other does not.
        """
        self.sale("150.00")
        extra = self.sale("40.00")
        self.assert_agrees()
        self.assertEqual(self.cari.cached_balance, Decimal("190.00"))

        extra.is_void = True
        extra.save()

        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("150.00"))
        self.assert_agrees()

        shown = [r["mv"].pk for r in self.client.get(
            reverse("accounts:statement", kwargs={"pk": self.cari.pk})
        ).context["rows"]]
        self.assertNotIn(extra.pk, shown,
                         "a voided row must leave the statement too")

    def test_a_voided_row_is_still_reachable_as_history(self):
        """Voided, not deleted — the cancelled filter is what it is for."""
        self.sale("150.00")
        extra = self.sale("40.00")
        extra.is_void = True
        extra.save()

        response = self.client.get(
            reverse("accounts:statement", kwargs={"pk": self.cari.pk}),
            {"status": "cancelled"})
        self.assertEqual([r["mv"].pk for r in response.context["rows"]], [extra.pk])

    def test_an_account_with_nothing_voided_shows_its_rows(self):
        """A membership rule that accidentally excluded everything would
        also satisfy "the two numbers agree" — at zero. Pin that the rows
        actually survive it."""
        self.sale("57.01")
        rows = self.client.get(
            reverse("accounts:statement", kwargs={"pk": self.cari.pk})
        ).context["rows"]
        self.assertEqual(len(rows), 1)
        self.assert_agrees()
