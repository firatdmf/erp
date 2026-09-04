# to run this test, use the command:
# python manage.py test accounting.test_expense_detail

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
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
from accounting.models_accounts import CariAccount, CariMovement


class ExpenseDetailPageTests(TestCase):
    """The page a saved expense lands on shows the entry, not a form.

    Landing back on the form said nothing about whether the entry was
    written: the same fields, still editable, with a save button under
    them. These pin down that the save now lands somewhere read-only, and
    that the page shows the other half of the entry — the cash the account
    gave up, or the debt the book took on — read off the ledger.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="detail", password="pw"
        )
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        StakeholderBook.objects.create(
            book=self.book, member=self.user.member, shares=1
        )
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Kasa", currency=self.usd,
            balance=Decimal("1000.00"),
        )
        self.firat = CariAccount.objects.create(
            book=self.book, code="FIRAT", name="MUHAMMED FIRAT ÖZTÜRK",
            type="customer", default_currency=self.usd,
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.lira_kasa = CashAccount.objects.create(
            book=self.book, name="Lira Kasa", currency=self.try_,
            balance=Decimal("100000.00"),
        )
        self.taxes = ExpenseCategory.objects.create(name="Taxes")

    def _add(self, **overrides):
        payload = {
            "book": self.book.pk, "category": self.taxes.pk,
            "cash_account": self.kasa.pk, "paid_by_cari": "",
            "currency": self.usd.pk, "amount": "180.59",
            "date": "2026-08-26", "exchange_rate": "",
            "description": "GELİR VERGİSİ S. (MUHTASAR)",
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
            payload,
        )

    def _detail(self, expense):
        return self.client.get(reverse(
            "accounting:equity_expense_detail",
            kwargs={"pk": self.book.pk, "expense_pk": expense.pk},
        ))

    # -- where a save lands -------------------------------------------------
    def test_recording_an_expense_lands_on_its_own_page(self):
        response = self._add()

        expense = EquityExpense.objects.get()
        self.assertRedirects(
            response,
            reverse("accounting:equity_expense_detail",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
        )

    def test_editing_an_expense_lands_on_its_own_page(self):
        self._add()
        expense = EquityExpense.objects.get()

        response = self.client.post(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
            {
                "book": self.book.pk, "category": self.taxes.pk,
                "cash_account": self.kasa.pk, "paid_by_cari": "",
                "currency": self.usd.pk, "amount": "200.00",
                "date": "2026-08-26", "exchange_rate": "",
                "description": "GELİR VERGİSİ S. (MUHTASAR)",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounting:equity_expense_detail",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
        )

    def test_the_page_it_lands_on_has_nothing_to_submit_the_expense_with(self):
        """The whole point: no form over these fields.

        The two forms on the page are the delete button — a POST, because
        a link a crawler can follow must not unwind a ledger entry — and
        whatever the site chrome carries. Neither offers the amount, and
        that is what is being pinned: an expense cannot be re-saved from
        here by pressing return.
        """
        self._add()
        expense = EquityExpense.objects.get()

        html = self._detail(expense).content.decode()

        self.assertNotIn('name="amount"', html)
        self.assertNotIn('id_paid_by_cari', html)
        self.assertIn(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
            html,
        )

    # -- what it shows ------------------------------------------------------
    def test_a_cash_expense_shows_the_account_it_left(self):
        self._add()
        expense = EquityExpense.objects.get()

        response = self._detail(expense)

        self.assertContains(response, "180.59")
        self.assertContains(response, "Kasa")
        self.assertContains(response, "GELİR VERGİSİ S. (MUHTASAR)")
        self.assertEqual(
            response.context["cash_entry"],
            CashTransactionEntry.objects.get(),
        )
        self.assertIsNone(response.context["ledger_movement"])

    def test_an_expense_on_account_shows_the_ledger_row_it_posted(self):
        self._add(cash_account="", paid_by_cari=self.firat.pk)
        expense = EquityExpense.objects.get()

        response = self._detail(expense)

        movement = CariMovement.objects.get()
        self.assertEqual(response.context["ledger_movement"], movement)
        self.assertIsNone(response.context["cash_entry"])
        self.assertContains(response, self.firat.code)
        self.assertContains(response, reverse(
            "accounts:movement_detail", args=[self.firat.pk, movement.pk]
        ))

    # -- scoping ------------------------------------------------------------
    def test_reaching_it_through_another_books_url_is_a_404(self):
        self._add()
        expense = EquityExpense.objects.get()
        other = Book.objects.create(name="Other", base_currency=self.usd)

        response = self.client.get(reverse(
            "accounting:equity_expense_detail",
            kwargs={"pk": other.pk, "expense_pk": expense.pk},
        ))

        self.assertEqual(response.status_code, 404)

    # -- the rate, and what it came to --------------------------------------
    def test_the_rate_row_carries_the_base_currency_equivalent(self):
        """One row answers both halves of the question.

        A rate on its own asks the reader to multiply; the converted
        figure on its own hides what it was arrived at.
        """
        self._add(cash_account=self.lira_kasa.pk, currency=self.try_.pk,
                  amount="4000.00", exchange_rate="0.025")
        expense = EquityExpense.objects.get()

        response = self._detail(expense)

        conversion = response.context["conversion"]
        self.assertEqual(conversion["rate"], Decimal("0.025000"))
        self.assertEqual(conversion["amount"], Decimal("100.00"))
        self.assertEqual(conversion["base_currency"], self.usd)
        self.assertContains(response, "0.025")
        self.assertContains(response, "$100.00")

    def test_both_figures_come_off_the_posted_row(self):
        """Nothing on this page is converted by this page.

        A blank rate on the expense is not the absence of one — it means
        "use the published rate for the date", and the row that posted is
        where that resolved. So the row is asked for both the rate and the
        figure, and neither is worked out here from the amount.
        """
        with mock.patch("accounting.services.get_exchange_rate") as published:
            published.return_value = Decimal("0.02")
            self._add(cash_account=self.lira_kasa.pk, currency=self.try_.pk,
                      amount="4000.00", exchange_rate="")
        expense = EquityExpense.objects.get()

        self.assertIsNone(expense.exchange_rate)

        conversion = self._detail(expense).context["conversion"]
        self.assertEqual(conversion["rate"], Decimal("0.020000"))
        self.assertEqual(conversion["amount"], Decimal("80.00"))

    def test_an_expense_in_the_books_own_currency_states_no_rate(self):
        self._add()
        expense = EquityExpense.objects.get()

        response = self._detail(expense)

        self.assertIsNone(response.context["conversion"])
        self.assertNotContains(response, "Exchange rate")

    def test_an_expense_that_posted_nothing_states_no_rate(self):
        """Rather than say what it would have come to.

        A figure this page worked out is this page's arithmetic, not the
        ledger's, and printing one where the ledger holds none is how a
        page comes to contradict the statement it describes.
        """
        self._add(cash_account=self.lira_kasa.pk, currency=self.try_.pk,
                  amount="4000.00", exchange_rate="0.025")
        expense = EquityExpense.objects.get()
        CashTransactionEntry.objects.all().delete()

        response = self._detail(expense)

        self.assertIsNone(response.context["conversion"])
        self.assertNotContains(response, "Exchange rate")
