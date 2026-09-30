# to run this test, use the command:
# python manage.py test accounting.tests.test_balance_close_limit

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CurrencyCategory, CurrencyExchangeRate, CurrentAccount, CurrentAccountMovement,
)


class BalanceCloseLimitTest(TestCase):
    """A closing difference is held to 1% of the account's trading, at least $3."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="close_limit", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.user.member.books.add(self.book)
        self.customer = self.account("C-1", "customer", self.usd)
        self.supplier = self.account("S-1", "supplier", self.usd)

    def account(self, code, type_, currency):
        return CurrentAccount.objects.create(
            book=self.book, code=code, name=code, type=type_, default_currency=currency)

    def row(self, account, amount, movement_type, currency=None):
        return CurrentAccountMovement.objects.create(
            current_account=account, book=self.book, date="2026-09-30",
            amount=Decimal(amount), currency=currency or self.usd, movement_type=movement_type)

    def post_close(self, account, amount, direction, currency=None):
        return self.client.post(
            reverse("accounts:movement_create", kwargs={"pk": account.pk}), {
                "amount": amount, "direction": direction, "movement_type": "balance_close",
                "currency": (currency or account.default_currency).pk, "date": "2026-09-30",
            }, follow=True)

    def closes(self, account):
        return account.movements.filter(movement_type="balance_close").count()

    def test_within_one_percent_of_trading_is_allowed(self):
        self.row(self.customer, "1000.00", "invoice_sale")
        self.post_close(self.customer, "10.00", "credit")
        self.assertEqual(self.closes(self.customer), 1)

    def test_above_one_percent_is_refused_and_points_a_customer_to_bad_debt(self):
        self.row(self.customer, "1000.00", "invoice_sale")
        response = self.post_close(self.customer, "10.01", "credit")
        self.assertEqual(self.closes(self.customer), 0)
        self.assertContains(response, "10.00 USD")
        self.assertContains(response, "Bad Debt Written Off")

    def test_a_small_account_can_always_close_three_dollars(self):
        self.row(self.customer, "50.00", "invoice_sale")
        self.post_close(self.customer, "3.00", "credit")
        self.assertEqual(self.closes(self.customer), 1)
        response = self.post_close(self.customer, "3.01", "credit")
        self.assertEqual(self.closes(self.customer), 1)
        self.assertContains(response, "3.00 USD")

    def test_a_large_cut_from_a_supplier_points_to_discount_or_return(self):
        self.row(self.supplier, "-1000.00", "invoice_purchase")
        response = self.post_close(self.supplier, "50.00", "debit")
        self.assertEqual(self.closes(self.supplier), 0)
        self.assertContains(response, "use Discount")
        self.assertContains(response, "Purchase Return")

    def test_collections_do_not_count_as_trading(self):
        self.row(self.customer, "100.00", "invoice_sale")
        self.row(self.customer, "-90.00", "collection")
        # 1% of 100 is 1, so the $3 floor applies — not 1% of 190.
        response = self.post_close(self.customer, "3.50", "credit")
        self.assertEqual(self.closes(self.customer), 0)
        self.assertContains(response, "3.00 USD")

    def test_the_limit_is_shown_in_the_accounts_own_currency(self):
        CurrencyExchangeRate.objects.create(
            from_currency="EUR", to_currency="USD", rate=Decimal("1.250000"), date="2026-09-30")
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="EUR", rate=Decimal("0.800000"), date="2026-09-30")
        greek = self.account("E-1", "customer", self.eur)
        self.row(greek, "2000.00", "invoice_sale", currency=self.eur)   # $2,500 traded
        response = self.post_close(greek, "30.00", "credit")            # $37.50 > $25
        self.assertEqual(self.closes(greek), 0)
        self.assertContains(response, "20.00 EUR")
        self.post_close(greek, "20.00", "credit")                       # $25.00
        self.assertEqual(self.closes(greek), 1)

    def test_an_old_oversized_row_still_saves_unchanged(self):
        self.row(self.customer, "100.00", "invoice_sale")
        old = self.row(self.customer, "-40.00", "balance_close")    # from before the limit
        self.client.post(
            reverse("accounts:movement_edit", kwargs={"pk": self.customer.pk, "mv_pk": old.pk}), {
                "amount": "40.00", "direction": "credit", "movement_type": "balance_close",
                "currency": self.usd.pk, "date": "2026-09-30", "description": "typo fixed",
            })
        old.refresh_from_db()
        self.assertEqual(old.description, "typo fixed")
