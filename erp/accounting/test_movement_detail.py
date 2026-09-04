# to run this test, use the command:
# python manage.py test accounting.test_movement_detail

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory, EquityExpense
from accounting.models_accounts import CariAccount, CariMovement, Payment


class MovementDetailTests(TestCase):
    """A ledger row needs a page of its own.

    The tables print it across a handful of columns, and a row is a thing
    you can be wrong about — so there has to be somewhere to see what it
    converted at and to correct it. What "correct it" means depends on
    whether a document owns the row, which is _movement_owner's rule.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mvd", password="pw"
        )
        self.client.force_login(self.user)
        self.member = self.user.member
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        # Object pages are refused unless the viewer is assigned the
        # row's book (accounting.book_scope.book_guarded).
        self.user.member.books.add(self.book)
        self.cari = CariAccount.objects.create(
            book=self.book, code="FIRAT", name="MUHAMMED FIRAT ÖZTÜRK",
            type="customer", default_currency=self.usd,
        )

    def _manual(self, amount="-939.70", currency=None, rate=None, base=None):
        mv = CariMovement(
            cari=self.cari, book=self.book, date="2026-08-26",
            amount=Decimal(amount), currency=currency or self.try_,
            movement_type="adjustment", description="stopaj",
            created_by=self.member,
        )
        if rate is not None:
            mv.exchange_rate = Decimal(rate)
            mv.amount_base = Decimal(base)
        mv.save()
        return mv

    def _url(self, mv):
        return reverse("accounts:movement_detail",
                       kwargs={"pk": self.cari.pk, "mv_pk": mv.pk})

    # -- the account page gets there ---------------------------------------
    def test_the_account_page_links_each_row_to_its_movement(self):
        mv = self._manual(rate="0.020790", base="-19.54")

        response = self.client.get(
            reverse("accounts:detail", kwargs={"pk": self.cari.pk})
        )

        self.assertContains(response, self._url(mv))
        self.assertContains(response, f">{mv.pk}</a>")

    # -- what the page says ------------------------------------------------
    def test_it_states_the_rate_and_what_the_row_came_to(self):
        mv = self._manual(rate="0.020790", base="-19.54")

        html = self.client.get(self._url(mv)).content.decode()

        self.assertIn("939.70", html)
        self.assertIn("19.54", html)
        self.assertIn("0.02079", html)

    def test_the_balance_after_counts_this_row_in(self):
        self._manual(amount="-100.00", currency=self.usd)
        mv = self._manual(amount="-50.00", currency=self.usd)

        response = self.client.get(self._url(mv))

        self.assertEqual(response.context["balance_after"], Decimal("-150.00"))

    # -- who may edit it ---------------------------------------------------
    def test_a_hand_entered_row_is_edited_here(self):
        mv = self._manual()

        response = self.client.get(self._url(mv))

        self.assertTrue(response.context["row"]["editable"])
        self.assertContains(
            response,
            reverse("accounts:movement_edit",
                    kwargs={"pk": self.cari.pk, "mv_pk": mv.pk}),
        )

    def test_a_row_a_payment_posted_sends_you_to_the_payment(self):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-2026-000075",
            type="collection", method="cash", status="draft",
            date="2026-08-26", amount=Decimal("180.59"), currency=self.usd,
        )
        payment.confirm()
        mv = payment.posted_movement

        response = self.client.get(self._url(mv))

        self.assertFalse(response.context["row"]["editable"])
        self.assertContains(
            response, reverse("accounts:payment_edit", args=[payment.pk])
        )
        self.assertNotContains(
            response,
            reverse("accounts:movement_edit",
                    kwargs={"pk": self.cari.pk, "mv_pk": mv.pk}),
        )

    def test_a_row_an_expense_posted_sends_you_to_the_expense(self):
        """This used to be a dead end — _movement_owner had no route for an
        expense, so the row said "linked document" and offered nowhere."""
        kasa = CashAccount.objects.create(
            book=self.book, name="Kasa", currency=self.usd,
            balance=Decimal("1000.00"),
        )
        self.assertTrue(kasa.pk)
        expense = EquityExpense.objects.create(
            book=self.book, currency=self.try_, amount=Decimal("939.70"),
            date="2026-08-26", paid_by_cari=self.cari, description="stopaj",
        )
        mv = CariMovement.objects.create(
            cari=self.cari, book=self.book, date=expense.date,
            amount=Decimal("-939.70"), currency=self.try_,
            movement_type="adjustment",
            source_type=ContentType.objects.get_for_model(EquityExpense),
            source_id=expense.pk,
        )

        response = self.client.get(self._url(mv))

        self.assertFalse(response.context["row"]["editable"])
        self.assertContains(
            response,
            reverse("accounting:equity_expense_detail",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
        )

    def test_a_movement_of_another_account_is_a_404(self):
        other = CariAccount.objects.create(
            book=self.book, code="X", name="Someone else",
            type="other", default_currency=self.usd,
        )
        mv = self._manual()

        response = self.client.get(
            reverse("accounts:movement_detail",
                    kwargs={"pk": other.pk, "mv_pk": mv.pk})
        )

        self.assertEqual(response.status_code, 404)
