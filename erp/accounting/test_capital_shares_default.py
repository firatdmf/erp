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
    ShareIssuance,
    StakeholderBook,
)
from authentication.models import Member


class CapitalDoesNotTouchSharesTest(TestCase):
    """A contribution and an equity issuance are separate events.

    Capital records cash going in. Shares move only through
    ShareIssuance rows on the book's shares page, where the change is
    dated and attributed.
    """

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
            member=self.member, book=self.book, shares=0
        )
        ShareIssuance.objects.create(
            stakeholder=self.holding, shares=10000000, date="2026-08-19",
            reason="opening",
        )
        self.holding.refresh_from_db()

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

    def test_the_form_does_not_ask_about_shares(self):
        form = self.client.get(self.url()).context["form"]
        self.assertNotIn("new_shares_issued", form.fields)

    def test_capital_posts_without_mentioning_shares(self):
        response = self.client.post(self.url(), self.payload())
        self.assertEqual(response.status_code, 302)
        capital = EquityCapital.objects.get()
        self.assertEqual(capital.amount, Decimal("600.00"))
        self.assertEqual(capital.new_shares_issued, 0)

    def test_the_holding_is_untouched(self):
        self.client.post(self.url(), self.payload())
        self.holding.refresh_from_db()
        self.assertEqual(self.holding.shares, 10000000)

    def test_a_posted_share_count_is_ignored(self):
        """The field is off the form, so a crafted post must not move
        ownership through the back door."""
        self.client.post(self.url(), self.payload(new_shares_issued="5000000"))
        self.holding.refresh_from_db()
        self.assertEqual(self.holding.shares, 10000000)
        self.assertEqual(EquityCapital.objects.get().new_shares_issued, 0)

    def test_the_cash_lands_in_the_account(self):
        self.client.post(self.url(), self.payload())
        self.cash.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal("600.00"))

    def test_a_non_stakeholder_still_cannot_contribute(self):
        outsider = get_user_model().objects.create_user(username="yabanci", password="pw")
        response = self.client.post(
            self.url(), self.payload(member=Member.objects.get(user=outsider).pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("member", response.context["form"].errors)

    def test_the_model_defaults_to_zero(self):
        capital = EquityCapital.objects.create(
            book=self.book, member=self.member, date_invested="2026-08-19",
            cash_account=self.cash, currency=self.usd, amount=Decimal("50.00"),
        )
        self.assertEqual(capital.new_shares_issued, 0)
