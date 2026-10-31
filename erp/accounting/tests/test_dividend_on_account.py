# to run this test, use the command:
# python manage.py test accounting.tests.test_dividend_on_account

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityDivident,
    StakeholderBook,
)
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement, Payment
from accounting.models_ledger import JournalLine
from accounting.services_ledger import ensure_chart


class DividendPaidOnAccountTests(TestCase):
    """A dividend somebody who owes the book paid the owner directly.

    A marketplace paying a seller's payout into the owner's own bank is
    the case in hand: no cash account of the book's ever holds the money.
    What the book is owed goes down by what they paid, and the owner has
    taken that much out — Owner Drawings (3300) against the Current
    Accounts control, no cash anywhere.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="dividend_on_account", password="pw"
        )
        self.client.force_login(self.user)
        self.member = self.user.member
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        StakeholderBook.objects.create(book=self.book, member=self.member, shares=1)
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Drawer", currency=self.usd, balance=Decimal("1000.00"),
        )
        self.etsy = CurrentAccount.objects.create(
            book=self.book, code="ETSY", name="Etsy", type="customer",
            default_currency=self.usd,
        )
        # Etsy owes the book for what it sold.
        CurrentAccountMovement.objects.create(
            current_account=self.etsy, book=self.book, date="2026-10-01",
            amount=Decimal("300.00"), currency=self.usd, movement_type="opening",
        )

    def _post(self, **overrides):
        payload = {
            "book": self.book.pk, "member": self.member.pk,
            "cash_account": "", "paid_by_current_account": self.etsy.pk,
            "currency": "", "amount": "120.00", "date": "2026-10-31",
            "exchange_rate": "", "description": "Etsy deposit",
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounting:add_equity_divident", kwargs={"pk": self.book.pk}),
            payload,
        )

    def _movement(self, dividend):
        return CurrentAccountMovement.objects.filter(
            source_type=ContentType.objects.get_for_model(EquityDivident),
            source_id=dividend.pk,
        )

    def _etsy_balance(self):
        self.etsy.refresh_from_db()
        return self.etsy.recompute_balance(save=False)

    def test_the_form_offers_the_books_current_accounts(self):
        other = Book.objects.create(name="Other", base_currency=self.usd)
        CurrentAccount.objects.create(
            book=other, code="X", name="Somebody Else", type="other",
            default_currency=self.usd,
        )
        response = self.client.get(
            reverse("accounting:add_equity_divident", kwargs={"pk": self.book.pk})
        )
        self.assertContains(response, "id_paid_by_current_account")
        self.assertContains(response, "Etsy")
        self.assertNotContains(response, "Somebody Else")

    def test_the_page_is_the_expense_pages_layout(self):
        response = self.client.get(
            reverse("accounting:add_equity_divident", kwargs={"pk": self.book.pk})
        )
        self.assertTemplateUsed(response, "accounting/partials/pf_entry_form_css.html")
        self.assertContains(response, 'id="fundCurrentAccount"')
        self.assertContains(response, 'id="currentAccountSearch"')

    def test_saving_lands_on_the_dividend(self):
        response = self._post()
        dividend = EquityDivident.objects.get()
        self.assertRedirects(response, reverse(
            "accounting:equity_dividend_detail",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))

    def test_the_edit_page_opens_on_the_account_that_paid(self):
        self._post()
        dividend = EquityDivident.objects.get()
        response = self.client.get(reverse(
            "accounting:edit_equity_dividend",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))
        self.assertTemplateUsed(response, "accounting/add_equity_divident.html")
        html = response.content.decode()
        self.assertRegex(html, r'<input type="radio"[^>]*id="fundCurrentAccount"\s+checked')
        self.assertRegex(html, r'<option value="%d"[^>]*selected' % self.etsy.pk)
        self.assertContains(response, 'value="2026-10-31"')
        self.assertContains(response, reverse(
            "accounting:delete_equity_dividend",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))

    def test_it_moves_no_cash(self):
        self._post()
        dividend = EquityDivident.objects.get()
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("1000.00"))
        self.assertFalse(CashTransactionEntry.objects.exists())
        self.assertEqual(dividend.currency, self.usd)

    def test_it_lowers_what_the_account_owes(self):
        self._post()
        movement = self._movement(EquityDivident.objects.get()).get()
        self.assertEqual(movement.amount, Decimal("-120.00"))
        self.assertEqual(movement.movement_type, "adjustment")
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(self._etsy_balance(), Decimal("180.00"))

    def test_the_ledger_reads_it_as_owner_drawings(self):
        self._post()
        movement = self._movement(EquityDivident.objects.get()).get()
        lines = {
            line.account.code: (line.debit, line.credit)
            for line in JournalLine.objects.filter(
                entry__source_type=ContentType.objects.get_for_model(CurrentAccountMovement),
                entry__source_id=movement.pk,
            ).select_related("account")
        }
        self.assertEqual(lines["3300"], (Decimal("120.00"), Decimal("0")))
        self.assertEqual(lines["1200"], (Decimal("0"), Decimal("120.00")))
        self.assertNotIn("1000", lines)

    def test_the_detail_page_shows_the_row_it_posted(self):
        self._post()
        dividend = EquityDivident.objects.get()
        response = self.client.get(reverse(
            "accounting:equity_dividend_detail",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))
        self.assertContains(response, "Etsy")
        self.assertContains(response, reverse(
            "accounts:movement_detail",
            args=[self.etsy.pk, self._movement(dividend).get().pk],
        ))

    def test_editing_the_amount_moves_the_balance_with_it(self):
        self._post()
        dividend = EquityDivident.objects.get()
        self.client.post(
            reverse("accounting:edit_equity_dividend",
                    kwargs={"pk": self.book.pk, "source_pk": dividend.pk}),
            {"book": self.book.pk, "member": self.member.pk, "cash_account": "",
             "paid_by_current_account": self.etsy.pk, "currency": self.usd.pk,
             "amount": "150.00", "date": "2026-10-31", "exchange_rate": "",
             "description": "Etsy deposit"},
        )
        self.assertEqual(
            list(self._movement(dividend).values_list("amount", flat=True)),
            [Decimal("-150.00")],
        )
        self.assertEqual(self._etsy_balance(), Decimal("150.00"))

    def test_moving_it_to_cash_takes_the_cash_and_drops_the_row(self):
        self._post()
        dividend = EquityDivident.objects.get()
        self.client.post(
            reverse("accounting:edit_equity_dividend",
                    kwargs={"pk": self.book.pk, "source_pk": dividend.pk}),
            {"book": self.book.pk, "member": self.member.pk,
             "cash_account": self.kasa.pk, "paid_by_current_account": "",
             "currency": self.usd.pk, "amount": "120.00", "date": "2026-10-31",
             "exchange_rate": "", "description": "Etsy deposit"},
        )
        self.assertFalse(self._movement(dividend).exists())
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("880.00"))
        self.assertEqual(self._etsy_balance(), Decimal("300.00"))

    def test_deleting_it_gives_the_balance_back(self):
        self._post()
        dividend = EquityDivident.objects.get()
        self.client.post(reverse(
            "accounting:delete_equity_dividend",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))
        self.assertFalse(EquityDivident.objects.exists())
        self.assertFalse(CurrentAccountMovement.objects.filter(
            source_type=ContentType.objects.get_for_model(EquityDivident)).exists())
        self.assertEqual(self._etsy_balance(), Decimal("300.00"))

    def test_the_ledger_row_links_back_to_the_dividend(self):
        self._post()
        dividend = EquityDivident.objects.get()
        movement = self._movement(dividend).get()
        response = self.client.get(
            reverse("accounts:movement_detail", args=[self.etsy.pk, movement.pk])
        )
        # Corrected on the dividend, which reposts it, never on the row.
        self.assertFalse(response.context["row"]["editable"])
        self.assertContains(response, reverse(
            "accounting:equity_dividend_detail",
            kwargs={"pk": self.book.pk, "source_pk": dividend.pk},
        ))

    def test_naming_both_funding_sources_is_rejected(self):
        response = self._post(cash_account=self.kasa.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquityDivident.objects.exists())

    def test_naming_neither_funding_source_is_rejected(self):
        response = self._post(paid_by_current_account="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquityDivident.objects.exists())

    def test_the_database_refuses_an_unfunded_dividend(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            EquityDivident.objects.create(
                book=self.book, currency=self.usd, amount=Decimal("1.00"),
                date="2026-10-31",
            )

    def test_a_dividend_paid_from_cash_still_takes_the_cash(self):
        self._post(cash_account=self.kasa.pk, paid_by_current_account="")
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("880.00"))
        self.assertTrue(CashTransactionEntry.objects.exists())
        self.assertFalse(self._movement(EquityDivident.objects.get()).exists())

    def test_a_cash_dividend_the_drawer_cannot_cover_is_refused(self):
        response = self._post(cash_account=self.kasa.pk, paid_by_current_account="",
                              amount="5000.00")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquityDivident.objects.exists())
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("1000.00"))
