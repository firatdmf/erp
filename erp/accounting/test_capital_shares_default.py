# to run this test, use the command:
# python manage.py test accounting.test_capital_shares_default

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CurrencyCategory,
    EquityCapital,
    StakeholderBook,
)
from authentication.models import Member


class CapitalWithoutIssuingSharesTest(TestCase):
    """Putting cash into a book should not force a share decision."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="cap_tester", password="pw")
        self.client.force_login(self.user)

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", total_shares=10000000)
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("0.00")
        )

        owner = User.objects.create_user(username="cuma", password="pw")
        owner.first_name, owner.last_name = "Cuma", "Öztürk"
        owner.save()
        self.member = Member.objects.get(user=owner)
        self.holding = StakeholderBook.objects.create(
            member=self.member, book=self.book, shares=10000000
        )

    def url(self):
        return reverse("accounting:add_equity_capital", kwargs={"pk": self.book.pk})

    def payload(self, **over):
        data = {
            "book": self.book.pk,
            "member": self.member.pk,
            "date_invested": "2026-08-19",
            "cash_account": self.cash.pk,
            "amount": "600.00",
        }
        data.update(over)
        return data

    def test_the_field_is_optional_on_the_form(self):
        form = self.client.get(self.url()).context["form"]
        self.assertFalse(form.fields["new_shares_issued"].required)

    def test_capital_posts_with_the_field_left_blank(self):
        response = self.client.post(self.url(), self.payload(new_shares_issued=""))
        self.assertEqual(response.status_code, 302)
        capital = EquityCapital.objects.get()
        self.assertEqual(capital.amount, Decimal("600.00"))
        self.assertEqual(capital.new_shares_issued, 0)

    def test_a_blank_field_does_not_move_the_holding(self):
        """0 issued means the owner's stake is untouched — the whole
        point of the default."""
        self.client.post(self.url(), self.payload(new_shares_issued=""))
        self.holding.refresh_from_db()
        self.assertEqual(self.holding.shares, 10000000)

    def test_the_cash_lands_in_the_account(self):
        self.client.post(self.url(), self.payload(new_shares_issued=""))
        self.cash.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal("600.00"))

    def test_shares_can_still_be_issued_when_that_is_the_intent(self):
        self.holding.shares = 0
        self.holding.save()
        self.client.post(self.url(), self.payload(new_shares_issued="10000000"))
        self.holding.refresh_from_db()
        self.assertEqual(self.holding.shares, 10000000)

    def test_the_model_defaults_to_zero(self):
        capital = EquityCapital.objects.create(
            book=self.book, member=self.member, date_invested="2026-08-19",
            cash_account=self.cash, currency=self.usd, amount=Decimal("50.00"),
        )
        self.assertEqual(capital.new_shares_issued, 0)
