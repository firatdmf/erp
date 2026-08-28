# to run this test, use the command:
# python manage.py test accounting.test_expense_on_account

import re
from decimal import Decimal
from pathlib import Path
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

    def _post(self, follow=False, **overrides):
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
            payload, follow=follow,
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
        # Scoped to this select: the page has several, and an account pk can
        # collide with a currency pk in another one.
        block = re.search(
            r'id="id_paid_by_cari".*?</select>', html, re.S
        )
        self.assertIsNotNone(block, "no paid_by_cari select on the page")
        match = re.search(
            r'<option value="%d"(.*?)>' % self.lira_cari.pk, block.group(0), re.S
        )
        self.assertIsNotNone(match, "no option rendered for the TRY account")
        self.assertIn(f'data-currency="{self.try_.pk}"', match.group(1))
        self.assertIn('data-currency-code="TRY"', match.group(1))

    def test_the_script_carries_no_translatable_literals(self):
        """A {% trans %} tag inside a JS '...' literal breaks the page the
        moment its text has an apostrophe — and Turkish attaches suffixes
        with one (FIRAT'a), so a translation could break it later."""
        tpl = (
            Path(__file__).parent
            / "templates/accounting/add_equity_expense.html"
        ).read_text(encoding="utf-8")
        script = tpl[tpl.index("<script>"):tpl.rindex("</script>")]
        self.assertNotIn("{% trans", script)
        self.assertNotIn("{% translate", script)

    def test_the_page_offers_a_currency_control(self):
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )
        html = response.content.decode()
        block = re.search(r'id="id_currency".*?</select>', html, re.S)
        self.assertIsNotNone(block, "currency is not a select on the page")
        self.assertIn('data-code="TRY"', block.group(0))
        self.assertIn('data-code="USD"', block.group(0))

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

    # -- currency and rate -------------------------------------------------
    def test_a_current_account_only_proposes_its_currency(self):
        """The reason the control exists: Firat's account is in dollars, but
        the tax he settled was a lira bill."""
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(currency=self.try_.pk, amount="8689.69")

        expense = EquityExpense.objects.get()
        self.assertEqual(expense.paid_by_cari, self.firat)   # a USD account
        self.assertEqual(expense.currency, self.try_)
        movement = CariMovement.objects.get(cari=self.firat)
        self.assertEqual(movement.currency, self.try_)
        self.assertEqual(movement.amount, Decimal("-8689.69"))

    def test_a_current_account_fills_its_own_currency_in_when_none_is_sent(self):
        self._post(currency="", amount="800.00")
        self.assertEqual(EquityExpense.objects.get().currency, self.usd)

    def test_a_cash_account_overrules_the_currency_it_was_sent(self):
        """A cash balance is decremented without converting, so 180.59 USD
        out of a lira kasa would subtract 180.59 lira."""
        lira_kasa = CashAccount.objects.create(
            book=self.book, name="Lira Kasa", currency=self.try_,
            balance=Decimal("10000.00"),
        )
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(cash_account=lira_kasa.pk, paid_by_cari="",
                       currency=self.usd.pk, amount="800.00")

        expense = EquityExpense.objects.get()
        self.assertEqual(expense.currency, self.try_)
        lira_kasa.refresh_from_db()
        self.assertEqual(lira_kasa.balance, Decimal("9200.00"))

    def test_the_entry_is_denominated_by_the_account_that_funded_it(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(paid_by_cari=self.lira_cari.pk, currency="", amount="800.00")

        expense = EquityExpense.objects.get()
        self.assertEqual(expense.currency, self.try_)

    def test_a_typed_rate_reaches_the_movements_base_amount(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(
                paid_by_cari=self.lira_cari.pk, currency=self.try_.pk,
                amount="800.00", exchange_rate="0.030000",
            )

        movement = CariMovement.objects.get(cari=self.lira_cari)
        self.assertEqual(movement.exchange_rate, Decimal("0.030000"))
        self.assertEqual(movement.amount_base, Decimal("-24.00"))

    def test_a_blank_rate_leaves_the_published_one_to_apply(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.025")
            self._post(
                paid_by_cari=self.lira_cari.pk, currency=self.try_.pk,
                amount="800.00", exchange_rate="",
            )

        movement = CariMovement.objects.get(cari=self.lira_cari)
        self.assertEqual(movement.amount_base, Decimal("-20.00"))

    # -- where you land afterwards -----------------------------------------
    def test_it_says_what_it_recorded(self):
        response = self._post(follow=True)

        note = str(list(response.context["messages"])[0])
        self.assertIn("180.59 USD", note)
        self.assertIn(self.firat.name, note)

    # -- editing ------------------------------------------------------------
    def _edit(self, expense, **overrides):
        payload = {
            "book": self.book.pk, "category": self.taxes.pk,
            "cash_account": expense.cash_account_id or "",
            "paid_by_cari": expense.paid_by_cari_id or "",
            "currency": expense.currency_id, "amount": str(expense.amount),
            "date": expense.date.isoformat(), "exchange_rate": "",
            "description": expense.description,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
            payload,
        )

    def test_the_page_you_land_on_is_the_expense_itself(self):
        response = self._post()

        expense = EquityExpense.objects.get()
        self.assertRedirects(
            response,
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
            fetch_redirect_response=False,
        )

    def test_the_page_shows_the_row_it_posted(self):
        self._post()
        expense = EquityExpense.objects.get()

        response = self.client.get(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk})
        )
        self.assertContains(response, self.firat.code)
        self.assertContains(response, "180.59")

    def _select_block(self, html, select_id):
        m = re.search(r'id="%s".*?</select>' % select_id, html, re.S)
        self.assertIsNotNone(m, f"no {select_id} select on the page")
        return m.group(0)

    def test_the_edit_page_keeps_the_currency_that_was_recorded(self):
        """939.70 TRY settled through a DOLLAR account. The page proposes the
        account's currency as you pick one, which is right while writing an
        expense and wrong once one exists — it turned this back into USD.

        The overwrite happened in the browser, which this cannot run, so the
        assertion that matters is on `currency_is_settled`: that flag is the
        one thing the script consults before proposing. The rendered
        `selected` was always right; it just did not survive page load.
        """
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.020790")
            self._post(currency=self.try_.pk, amount="939.70")
        expense = EquityExpense.objects.get()
        self.assertEqual(expense.currency, self.try_)
        self.assertEqual(expense.paid_by_cari.default_currency, self.usd)

        response = self.client.get(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk})
        )

        self.assertTrue(response.context["currency_is_settled"])
        block = self._select_block(response.content.decode(), "id_currency")
        chosen = re.search(r'<option value="(\d+)"[^>]*\bselected\b', block)
        self.assertIsNotNone(chosen, "no currency is selected")
        self.assertEqual(int(chosen.group(1)), self.try_.pk)

    def test_the_edit_page_keeps_the_date_that_was_recorded(self):
        """form.data is empty on a GET, so falling back to today meant an
        edit opened on today and saved that over the real date."""
        self._post(date="2026-08-26")
        expense = EquityExpense.objects.get()

        response = self.client.get(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk})
        )

        self.assertEqual(response.context["date_value"], "2026-08-26")
        self.assertContains(response, 'value="2026-08-26"')

    def test_a_new_expense_still_opens_on_today_with_nothing_settled(self):
        response = self.client.get(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk})
        )

        self.assertFalse(response.context["currency_is_settled"])
        self.assertEqual(
            response.context["date_value"], timezone.localdate().isoformat()
        )

    def test_a_rejected_submit_keeps_what_was_typed(self):
        response = self.client.post(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
            {
                "book": self.book.pk, "category": self.taxes.pk,
                "cash_account": "", "paid_by_cari": "",   # rejected: unfunded
                "currency": self.try_.pk, "amount": "939.70",
                "date": "2026-08-26", "exchange_rate": "", "description": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["date_value"], "2026-08-26")
        self.assertTrue(response.context["currency_is_settled"])

    def test_editing_without_touching_the_currency_leaves_it_alone(self):
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.020790")
            self._post(currency=self.try_.pk, amount="939.70")
        expense = EquityExpense.objects.get()

        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.020790")
            self._edit(expense, description="stopaj")

        expense.refresh_from_db()
        self.assertEqual(expense.currency, self.try_)
        self.assertEqual(expense.amount, Decimal("939.70"))
        self.assertEqual(
            CariMovement.objects.get(cari=self.firat).currency, self.try_
        )

    def test_changing_the_amount_moves_the_debt_with_it(self):
        self._post()
        expense = EquityExpense.objects.get()

        self._edit(expense, amount="200.00")

        self.assertEqual(CariMovement.objects.filter(cari=self.firat).count(), 1)
        self.assertEqual(
            CariMovement.objects.get(cari=self.firat).amount, Decimal("-200.00")
        )
        self.firat.refresh_from_db()
        self.assertEqual(self.firat.cached_balance, Decimal("-200.00"))

    def test_moving_an_expense_from_cash_to_an_account_gives_the_cash_back(self):
        self._post(cash_account=self.kasa.pk, paid_by_cari="")
        expense = EquityExpense.objects.get()
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("819.41"))

        self._edit(expense, cash_account="", paid_by_cari=self.firat.pk)

        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("1000.00"))
        self.assertFalse(
            CashTransactionEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
            ).exists()
        )
        self.firat.refresh_from_db()
        self.assertEqual(self.firat.cached_balance, Decimal("-180.59"))

    def test_moving_an_expense_from_an_account_to_cash_clears_the_debt(self):
        self._post()
        expense = EquityExpense.objects.get()

        self._edit(expense, paid_by_cari="", cash_account=self.kasa.pk)

        self.assertFalse(CariMovement.objects.exists())
        self.firat.refresh_from_db()
        self.assertEqual(self.firat.cached_balance, Decimal("0.00"))
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("819.41"))

    def test_moving_between_cash_accounts_credits_the_one_it_left(self):
        second = CashAccount.objects.create(
            book=self.book, name="Bank", currency=self.usd,
            balance=Decimal("500.00"),
        )
        self._post(cash_account=self.kasa.pk, paid_by_cari="")
        expense = EquityExpense.objects.get()

        self._edit(expense, cash_account=second.pk)

        self.kasa.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("1000.00"))
        self.assertEqual(second.balance, Decimal("319.41"))
        self.assertEqual(
            CashTransactionEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(EquityExpense),
                content_pk=expense.pk,
            ).count(),
            1,
        )

    def test_an_expense_cannot_be_edited_through_another_books_url(self):
        self._post()
        expense = EquityExpense.objects.get()
        other = Book.objects.create(name="Other", base_currency=self.usd)

        response = self.client.get(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": other.pk, "expense_pk": expense.pk})
        )
        self.assertEqual(response.status_code, 404)

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
