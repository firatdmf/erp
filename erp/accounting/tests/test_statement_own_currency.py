"""A statement reads in the account's own currency.

Akdas Gardinen keeps a euro account in a dollar book. Her printed
statement said $1,243.64 — the dollar sum the ledger keeps — when what
she owes, and what her account page says, is €1,104.81. Every statement
(the printed sheet, its Excel, the page) now reads in the currency the
accounts keep when they all keep one, by the rule the account page
already used (CurrentAccount.in_own_currency); otherwise in base.

Run with:
    python manage.py test accounting.tests.test_statement_own_currency
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting import services
from accounting.models import Book, CurrencyCategory, CurrencyExchangeRate
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import combined_statement
from crm.models import Company


class EuroAccountBase(TestCase):
    def setUp(self):
        services._RATE_MEMO.clear()
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.user = get_user_model().objects.create_user(username="eur_st", password="pw")
        self.user.member.books.set([self.laleli, self.ergene])
        self.client.force_login(self.user)
        self.company = Company.objects.create(name="Akdas Gardinen")
        self.account = CurrentAccount.objects.create(
            book=self.laleli, code="ACC-099", name="Akdas Gardinen",
            company=self.company, default_currency=self.eur)
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="EUR", rate=Decimal("0.880000"), date="2026-10-20")

    def euros(self, amount, day, rate, account=None, **kw):
        account = account or self.account
        amount = Decimal(amount)
        return CurrentAccountMovement.objects.create(
            current_account=account, book=account.book, date=f"2026-10-{day:02d}",
            amount=amount, currency=self.eur, exchange_rate=Decimal(rate),
            amount_base=(amount * Decimal(rate)).quantize(Decimal("0.01")),
            movement_type=kw.pop("movement_type", "order_sale"), **kw)

    def the_three_orders(self):
        self.euros("430.10", 6, "1.13550000")
        self.euros("247.25", 19, "1.11950000")
        self.euros("427.46", 30, "1.11930000")


class CombinedStatementInEuros(EuroAccountBase):
    def test_a_euro_account_reads_in_euros(self):
        self.the_three_orders()
        data = combined_statement([self.account])
        self.assertEqual(data["currency_symbol"], "€")
        self.assertEqual(data["closing"], Decimal("1104.81"))
        self.assertEqual(data["debit_total"], Decimal("1104.81"))
        self.assertEqual([r["amount"] for r in data["rows"]],
                         [Decimal("430.10"), Decimal("247.25"), Decimal("427.46")])

    def test_a_dollar_row_counts_at_its_days_rate(self):
        self.euros("500.00", 6, "1.13550000")
        CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.laleli, date="2026-10-20",
            amount=Decimal("-100.00"), currency=self.usd, movement_type="payment")
        data = combined_statement([self.account])
        self.assertEqual(data["rows"][1]["amount"], Decimal("-88.00"))
        self.assertEqual(data["rows"][1]["own_rate"], Decimal("0.880000"))
        self.assertEqual(data["closing"], Decimal("412.00"))

    def test_a_revaluation_is_not_printed_to_the_customer(self):
        self.euros("500.00", 6, "1.13550000")
        CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.laleli, date="2026-10-20",
            amount=Decimal("12.00"), currency=self.usd, movement_type="fx_adjustment")
        data = combined_statement([self.account])
        self.assertEqual(len(data["rows"]), 1)
        self.assertEqual(data["closing"], Decimal("500.00"))

    def test_accounts_in_different_currencies_stay_in_base(self):
        dollars = CurrentAccount.objects.create(
            book=self.ergene, code="ACC-100", name="Akdas Gardinen",
            company=self.company, default_currency=self.usd)
        self.euros("100.00", 6, "1.13550000")
        CurrentAccountMovement.objects.create(
            current_account=dollars, book=self.ergene, date="2026-10-07",
            amount=Decimal("50.00"), currency=self.usd, movement_type="order_sale")
        data = combined_statement([self.account, dollars])
        self.assertEqual(data["currency_symbol"], "$")
        self.assertEqual(data["closing"], Decimal("163.55"))

    def test_the_printed_sheet_says_euros(self):
        self.the_three_orders()
        response = self.client.get(
            reverse("accounts:statement_print_combined") + f"?ids={self.account.pk}&html=1")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("€1,104.81", body)
        self.assertIn("€430.10", body)
        self.assertNotIn("$1,243.64", body)


class StatementPageInEuros(EuroAccountBase):
    def test_the_page_balance_reads_in_euros(self):
        self.the_three_orders()
        response = self.client.get(reverse("accounts:statement", args=[self.account.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["closing"], Decimal("1104.81"))
        self.assertEqual(response.context["debit_total"], Decimal("1104.81"))
        self.assertEqual(response.context["currency_symbol"], "€")

    def test_a_dollar_row_states_what_it_counted_in_euros(self):
        self.euros("500.00", 6, "1.13550000")
        CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.laleli, date="2026-10-20",
            amount=Decimal("-100.00"), currency=self.usd, movement_type="payment")
        response = self.client.get(reverse("accounts:statement", args=[self.account.pk]))
        self.assertContains(response, '<span class="st-fx">USD · €88.00 @ 0.88')
        # A euro row converted nothing, so it states nothing.
        self.assertContains(response, '<span class="st-fx">', count=1)

    def test_the_opening_balance_reads_in_euros_too(self):
        self.the_three_orders()
        response = self.client.get(reverse("accounts:statement", args=[self.account.pk]),
                                   {"date_from": "2026-10-10"})
        self.assertEqual(response.context["opening"], Decimal("430.10"))
        self.assertEqual(response.context["closing"], Decimal("1104.81"))

    def test_a_dollar_account_page_is_unchanged(self):
        self.account.default_currency = self.usd
        self.account.save()
        CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.laleli, date="2026-10-06",
            amount=Decimal("40.00"), currency=self.usd, movement_type="order_sale")
        response = self.client.get(reverse("accounts:statement", args=[self.account.pk]))
        self.assertEqual(response.context["closing"], Decimal("40.00"))
        self.assertEqual(response.context["currency_symbol"], "$")
