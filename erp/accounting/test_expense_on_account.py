# to run this test, use the command:
# python manage.py test accounting.test_expense_on_account

import re
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityExpense,
    ExpenseCategory,
    StakeholderBook,
)
from accounting.models_accounts import CariAccount, CariMovement, Payment


class ExpensePaidOnAccountTests(TestCase):
    """An expense somebody else settled credits them, not the cash box.

    The book owes whoever paid; it is not lighter on cash. Booking that
    against a cash account credited money that never moved and left the
    debt — already on their current account — as a second credit against
    one debit. These tests pin the entry down to one credit, on the side
    the money actually came from.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="on_account", password="pw"
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
        StakeholderBook.objects.create(book=self.book, member=self.member, shares=1)
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Kasa", currency=self.usd,
            balance=Decimal("1000.00"),
        )
        self.firat = CariAccount.objects.create(
            book=self.book, code="FIRAT", name="MUHAMMED FIRAT ÖZTÜRK",
            type="customer", default_currency=self.usd,
        )
        self.lira_cari = CariAccount.objects.create(
            book=self.book, code="ORTAK", name="Partner", type="other",
            default_currency=self.try_,
        )
        self.taxes = ExpenseCategory.objects.create(name="Taxes")

    def _post(self, **overrides):
        payload = {
            "book": self.book.pk, "category": self.taxes.pk,
            "cash_account": "", "paid_by_cari": self.firat.pk,
            "currency": self.usd.pk, "amount": "180.59",
            "date": "2026-08-26", "exchange_rate": "",
            "description": "GELİR VERGİSİ S. (MUHTASAR)",
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
            payload,
        )

    # -- the form offers both, and says what each is in --------------------
    def test_the_form_offers_both_funding_sources_scoped_to_the_book(self):
        other_book = Book.objects.create(name="Other", base_currency=self.usd)
        stranger = CariAccount.objects.create(
            book=other_book, code="X", name="Somebody Else",
            type="other", default_currency=self.usd,
        )
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )
        self.assertContains(response, "id_paid_by_cari")
        self.assertContains(response, self.firat.name)
        self.assertNotContains(response, stranger.name)

    def test_current_account_options_carry_their_currency(self):
        """The rate converter reads the currency off whichever select is
        filled, so a cari option has to state its own."""
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )
        html = response.content.decode()
        # The tag spans several lines in the template, so match the whole
        # element rather than a line of it.
        match = re.search(
            r'<option value="%d"(.*?)>' % self.lira_cari.pk, html, re.S
        )
        self.assertIsNotNone(match, "no option rendered for the TRY account")
        self.assertIn(f'data-currency="{self.try_.pk}"', match.group(1))
        self.assertIn('data-currency-code="TRY"', match.group(1))

    def test_the_page_opens_on_today_and_offers_the_search_picker(self):
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )
        html = response.content.decode()
        # A date object localized by the template renders as "28 Ağustos
        # 2026", which <input type="date"> silently drops.
        self.assertIn(f'value="{timezone.localdate().isoformat()}"', html)
        self.assertIn('id="cariSearch"', html)
        self.assertIn('id="cariChip"', html)

    # -- the cash box is not touched ---------------------------------------
    def test_it_moves_no_cash_and_writes_no_cash_entry(self):
        self._post()

        expense = EquityExpense.objects.get()
        self.assertIsNone(expense.cash_account)
        self.assertEqual(expense.paid_by_cari, self.firat)
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("1000.00"))
        self.assertFalse(
            CashTransactionEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
            ).exists()
        )

    # -- the credit lands on the account of whoever paid -------------------
    def test_it_credits_the_account_of_whoever_paid(self):
        self._post()

        expense = EquityExpense.objects.get()
        movement = CariMovement.objects.get(cari=self.firat)
        # Negative is what the cari detail page reads as a payable: the
        # book owes him, which is the whole reason the expense went in.
        self.assertEqual(movement.amount, Decimal("-180.59"))
        self.assertEqual(movement.date, expense.date)
        self.assertEqual(movement.source, expense)
        self.firat.refresh_from_db()
        self.assertEqual(self.firat.cached_balance, Decimal("-180.59"))

    def test_the_credit_is_an_adjustment_and_mirrors_to_no_payment(self):
        """Nothing was collected, so nothing belongs in the tahsilat list."""
        self._post()

        movement = CariMovement.objects.get(cari=self.firat)
        self.assertEqual(movement.movement_type, "adjustment")
        self.assertFalse(Payment.objects.exists())

    # -- currency and rate follow the account that funded it ---------------
    def test_the_entry_is_denominated_by_the_account_that_funded_it(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(paid_by_cari=self.lira_cari.pk, amount="800.00")

        expense = EquityExpense.objects.get()
        self.assertEqual(expense.currency, self.try_)

    def test_a_typed_rate_reaches_the_movements_base_amount(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(
                paid_by_cari=self.lira_cari.pk, amount="800.00",
                exchange_rate="0.030000",
            )

        movement = CariMovement.objects.get(cari=self.lira_cari)
        self.assertEqual(movement.exchange_rate, Decimal("0.030000"))
        self.assertEqual(movement.amount_base, Decimal("-24.00"))

    def test_a_blank_rate_leaves_the_published_one_to_apply(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(
                paid_by_cari=self.lira_cari.pk, amount="800.00", exchange_rate="",
            )

        movement = CariMovement.objects.get(cari=self.lira_cari)
        self.assertEqual(movement.amount_base, Decimal("-20.00"))

    # -- exactly one funding source ----------------------------------------
    def test_naming_both_funding_sources_is_rejected(self):
        response = self._post(cash_account=self.kasa.pk)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquityExpense.objects.exists())
        self.assertFalse(CariMovement.objects.exists())

    def test_naming_neither_funding_source_is_rejected(self):
        response = self._post(cash_account="", paid_by_cari="")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquityExpense.objects.exists())

    def test_the_database_refuses_an_unfunded_expense(self):
        """The constraint, not the view, is what makes this a fact."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EquityExpense.objects.create(
                    book=self.book, category=self.taxes, currency=self.usd,
                    amount=Decimal("10.00"), date="2026-08-26",
                )

    # -- the cash path still behaves --------------------------------------
    def test_an_expense_paid_from_cash_still_moves_cash(self):
        self._post(cash_account=self.kasa.pk, paid_by_cari="")

        expense = EquityExpense.objects.get()
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("819.41"))
        self.assertTrue(
            CashTransactionEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
            ).exists()
        )
        self.assertFalse(CariMovement.objects.exists())
