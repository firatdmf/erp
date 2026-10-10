"""The view, edit and delete pages of every cash source but payments and
expenses, which have their own.

None of the three had any: one entered by mistake could be neither
corrected nor removed without a shell on production.
"""
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CashAccount, CashTransactionEntry, CurrencyCategory, CurrencyExchange,
    EquityCapital, EquityDivident, EquityRevenue, InTransfer, StakeholderBook,
)
from accounting.views import handle_equity_transaction


class EquityRevenuePageTests(TestCase):

    def setUp(self):
        self.usd = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )[0]
        self.book = Book.objects.create(name="Laleli Fabric")
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("100.00")
        )
        self.vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        user = get_user_model().objects.create_superuser(username="teller", password="pw")
        self.client.force_login(user)
        self.revenue = EquityRevenue.objects.create(
            book=self.book, cash_account=self.kasa, currency=self.usd,
            amount=Decimal("340.00"), date="2026-09-28",
            description="entered by mistake", revenue_type="other",
        )
        handle_equity_transaction(
            self.book, self.revenue.amount, self.usd,
            self.revenue, self.revenue.pk, self.kasa,
        )
        self.ct = ContentType.objects.get_for_model(EquityRevenue)

    def url(self, name):
        return reverse(f"accounting:{name}", kwargs={
            "pk": self.book.pk, "source_pk": self.revenue.pk,
        })

    def entries(self):
        return CashTransactionEntry.objects.filter(
            content_type=self.ct, content_pk=self.revenue.pk
        )

    def balance(self, account):
        account.refresh_from_db()
        return account.balance

    def edit(self, **changes):
        data = {
            "book": self.book.pk, "currency": self.usd.pk,
            "cash_account": self.kasa.pk, "amount": "340.00",
            "date": "2026-09-28", "description": "entered by mistake",
            "revenue_type": "other", "order": "",
        }
        data.update(changes)
        return self.client.post(self.url("edit_equity_revenue"), data)

    def test_the_detail_page_offers_edit_and_delete(self):
        response = self.client.get(self.url("equity_revenue_detail"))
        self.assertContains(response, "entered by mistake")
        self.assertContains(response, self.url("edit_equity_revenue"))
        self.assertContains(response, self.url("delete_equity_revenue"))

    def test_the_edit_page_opens_on_the_stored_date(self):
        response = self.client.get(self.url("edit_equity_revenue"))
        self.assertContains(response, 'value="2026-09-28"')

    def test_another_books_revenue_is_a_404(self):
        other = Book.objects.create(name="Ergene")
        response = self.client.get(reverse(
            "accounting:equity_revenue_detail",
            kwargs={"pk": other.pk, "source_pk": self.revenue.pk},
        ))
        self.assertEqual(response.status_code, 404)

    def test_delete_takes_the_cash_back_out(self):
        self.assertEqual(self.balance(self.kasa), Decimal("440.00"))
        self.client.post(self.url("delete_equity_revenue"))
        self.assertFalse(EquityRevenue.objects.filter(pk=self.revenue.pk).exists())
        self.assertFalse(self.entries().exists())
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))
        JournalEntry = apps.get_model("accounting", "JournalEntry")
        self.assertFalse(JournalEntry.objects.filter(
            source_type=self.ct, source_id=self.revenue.pk
        ).exists())

    def test_delete_is_refused_once_the_money_has_been_spent(self):
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("200.00"))
        self.client.post(self.url("delete_equity_revenue"))
        self.assertTrue(EquityRevenue.objects.filter(pk=self.revenue.pk).exists())
        self.assertEqual(self.entries().count(), 1)
        self.assertEqual(self.balance(self.kasa), Decimal("200.00"))

    def test_editing_the_amount_reposts_it(self):
        response = self.edit(amount="300.00")
        self.assertRedirects(response, self.url("equity_revenue_detail"),
                             fetch_redirect_response=False)
        self.assertEqual(self.balance(self.kasa), Decimal("400.00"))
        self.assertEqual(list(self.entries().values_list("amount", flat=True)),
                         [Decimal("300.00")])

    def test_moving_it_to_another_account_moves_the_cash(self):
        self.edit(cash_account=self.vault.pk)
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))
        self.assertEqual(self.balance(self.vault), Decimal("340.00"))
        self.assertEqual(self.entries().get().cash_account_id, self.vault.pk)

    def test_a_move_the_old_account_cannot_cover_is_refused(self):
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("200.00"))
        response = self.edit(cash_account=self.vault.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(self.kasa), Decimal("200.00"))
        self.assertEqual(self.balance(self.vault), Decimal("0.00"))
        self.assertEqual(self.entries().get().cash_account_id, self.kasa.pk)

    def test_the_transactions_row_opens_the_revenue(self):
        response = self.client.get(reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        ))
        self.assertContains(
            response, f'data-href="{self.url("equity_revenue_detail")}"'
        )


class CashSourceFixture(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )[0]
        self.eur = CurrencyCategory.objects.get_or_create(
            code="EUR", defaults={"name": "Euro", "symbol": "€"}
        )[0]
        self.book = Book.objects.create(name="Laleli Fabric")
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("100.00")
        )
        self.vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        self.euros = CashAccount.objects.create(
            book=self.book, name="Cash EUR", currency=self.eur, balance=Decimal("0.00")
        )
        user = get_user_model().objects.create_superuser(username="teller", password="pw")
        self.member = user.member
        self.client.force_login(user)

    def url(self, name, obj):
        return reverse(f"accounting:{name}",
                       kwargs={"pk": self.book.pk, "source_pk": obj.pk})

    def balance(self, account):
        account.refresh_from_db()
        return account.balance

    def entries(self, obj):
        return CashTransactionEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(obj), content_pk=obj.pk
        )


class EquityCapitalPageTests(CashSourceFixture):

    def setUp(self):
        super().setUp()
        StakeholderBook.objects.get_or_create(member=self.member, book=self.book)
        self.capital = EquityCapital.objects.create(
            book=self.book, member=self.member, date_invested="2026-09-20",
            cash_account=self.kasa, currency=self.usd, amount=Decimal("500.00"),
            note="owner top-up",
        )
        handle_equity_transaction(
            self.book, self.capital.amount, self.usd,
            self.capital, self.capital.pk, self.kasa,
        )

    def edit(self, **changes):
        data = {
            "book": self.book.pk, "currency": self.usd.pk,
            "member": self.member.pk, "cash_account": self.kasa.pk,
            "amount": "500.00", "date_invested": "2026-09-20",
            "exchange_rate": "", "note": "owner top-up",
        }
        data.update(changes)
        return self.client.post(self.url("edit_equity_capital", self.capital), data)

    def test_the_detail_page_names_the_member(self):
        response = self.client.get(self.url("equity_capital_detail", self.capital))
        self.assertContains(response, str(self.member))
        self.assertContains(response, "owner top-up")
        self.assertContains(response, self.url("edit_equity_capital", self.capital))

    def test_the_edit_page_opens_on_the_stored_date(self):
        response = self.client.get(self.url("edit_equity_capital", self.capital))
        self.assertContains(response, 'value="2026-09-20"')

    def test_editing_the_amount_reposts_it(self):
        response = self.edit(amount="450.00")
        self.assertRedirects(response, self.url("equity_capital_detail", self.capital),
                             fetch_redirect_response=False)
        self.assertEqual(self.balance(self.kasa), Decimal("550.00"))
        self.assertEqual(list(self.entries(self.capital).values_list("amount", flat=True)),
                         [Decimal("450.00")])

    def test_delete_takes_the_cash_back_out(self):
        self.client.post(self.url("delete_equity_capital", self.capital))
        self.assertFalse(EquityCapital.objects.filter(pk=self.capital.pk).exists())
        self.assertFalse(self.entries(self.capital).exists())
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))

    def test_delete_is_refused_once_the_money_has_been_spent(self):
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("300.00"))
        self.client.post(self.url("delete_equity_capital", self.capital))
        self.assertTrue(EquityCapital.objects.filter(pk=self.capital.pk).exists())
        self.assertEqual(self.balance(self.kasa), Decimal("300.00"))

    def test_the_transactions_row_opens_the_deposit(self):
        response = self.client.get(reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        ))
        self.assertContains(
            response, f'data-href="{self.url("equity_capital_detail", self.capital)}"'
        )


class CurrencyExchangePageTests(CashSourceFixture):
    """100 USD out of Cash, 90 EUR into Cash EUR."""

    def setUp(self):
        super().setUp()
        self.client.post(
            reverse("accounting:make_currency_exchange", kwargs={"pk": self.book.pk}),
            {"book": self.book.pk, "from_cash_account": self.kasa.pk,
             "to_cash_account": self.euros.pk, "from_amount": "100.00",
             "to_amount": "90.00", "date": "2026-09-21"},
        )
        self.exchange = CurrencyExchange.objects.get()
        self.assertEqual(self.balance(self.kasa), Decimal("0.00"))
        self.assertEqual(self.balance(self.euros), Decimal("90.00"))

    # ── the general ledger ───────────────────────────────────────
    def _ledger(self):
        from accounting.services_ledger import reconcile
        cash = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1000")
        lines = {}
        from accounting.models_ledger import JournalLine
        for line in JournalLine.objects.filter(entry__book=self.book):
            lines[line.account.code] = (lines.get(line.account.code, Decimal("0"))
                                        + line.debit - line.credit)
        return cash, lines

    def test_an_exchange_posts_itself_and_cash_agrees_with_the_journal(self):
        """Cash leaves one account and reaches another; what the two legs
        are worth apart is the cost of the exchange."""
        from accounting.models_ledger import JournalEntry
        cash, lines = self._ledger()
        self.assertEqual(JournalEntry.objects.filter(book=self.book).count(), 1)
        self.assertEqual(cash["ledger"], cash["subsidiary"])
        rows = {r.is_amount_positive: r.amount_in_base_currency
                for r in self.entries(self.exchange)}
        self.assertEqual(lines["1000"], rows[True] - rows[False])
        self.assertEqual(lines.get("5900", Decimal("0")), rows[False] - rows[True])

    def test_editing_an_exchange_replaces_its_entry(self):
        from accounting.models_ledger import JournalEntry
        self.edit(to_amount="80.00")
        cash, _lines = self._ledger()
        self.assertEqual(JournalEntry.objects.filter(book=self.book).count(), 1)
        self.assertEqual(cash["ledger"], cash["subsidiary"])

    def test_deleting_an_exchange_takes_its_entry_with_it(self):
        from accounting.models_ledger import JournalEntry
        self.client.post(self.url("delete_equity_exchange", self.exchange))
        self.assertFalse(CurrencyExchange.objects.exists())
        self.assertFalse(JournalEntry.objects.filter(book=self.book).exists())

    def edit(self, **changes):
        data = {
            "book": self.book.pk, "from_cash_account": self.kasa.pk,
            "to_cash_account": self.euros.pk, "from_amount": "100.00",
            "to_amount": "90.00", "date": "2026-09-21",
        }
        data.update(changes)
        return self.client.post(self.url("edit_equity_exchange", self.exchange), data)

    def test_the_detail_page_shows_both_legs(self):
        response = self.client.get(self.url("equity_exchange_detail", self.exchange))
        self.assertContains(response, "Cash EUR")
        self.assertContains(response, "1 USD = 0.9")
        self.assertEqual(len(response.context["cash_entries"]), 2)

    def test_the_edit_page_opens_on_the_stored_date(self):
        response = self.client.get(self.url("edit_equity_exchange", self.exchange))
        self.assertContains(response, 'value="2026-09-21"')

    def test_editing_the_amounts_reposts_both_legs(self):
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("50.00"))
        response = self.edit(from_amount="120.00", to_amount="108.00")
        self.assertRedirects(response, self.url("equity_exchange_detail", self.exchange),
                             fetch_redirect_response=False)
        self.assertEqual(self.balance(self.kasa), Decimal("30.00"))
        self.assertEqual(self.balance(self.euros), Decimal("108.00"))
        self.assertEqual(
            sorted(self.entries(self.exchange).values_list("amount", flat=True)),
            [Decimal("108.00"), Decimal("120.00")],
        )

    def test_an_edit_the_source_cannot_cover_is_refused(self):
        response = self.edit(from_amount="150.00", to_amount="135.00")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(self.kasa), Decimal("0.00"))
        self.assertEqual(self.balance(self.euros), Decimal("90.00"))

    def test_the_same_account_on_both_sides_is_a_form_error(self):
        response = self.edit(to_cash_account=self.kasa.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_delete_puts_both_accounts_back(self):
        self.client.post(self.url("delete_equity_exchange", self.exchange))
        self.assertFalse(CurrencyExchange.objects.exists())
        self.assertFalse(self.entries(self.exchange).exists())
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))
        self.assertEqual(self.balance(self.euros), Decimal("0.00"))

    def test_delete_is_refused_once_the_euros_are_spent(self):
        CashAccount.objects.filter(pk=self.euros.pk).update(balance=Decimal("40.00"))
        self.client.post(self.url("delete_equity_exchange", self.exchange))
        self.assertTrue(CurrencyExchange.objects.exists())
        self.assertEqual(self.balance(self.kasa), Decimal("0.00"))
        self.assertEqual(self.balance(self.euros), Decimal("40.00"))


class EquityDividendPageTests(CashSourceFixture):

    def setUp(self):
        super().setUp()
        StakeholderBook.objects.get_or_create(member=self.member, book=self.book)
        self.dividend = EquityDivident.objects.create(
            book=self.book, member=self.member, cash_account=self.kasa,
            currency=self.usd, amount=Decimal("60.00"), date="2026-09-22",
            description="September draw",
        )
        handle_equity_transaction(
            self.book, self.dividend.amount, self.usd,
            self.dividend, self.dividend.pk, self.kasa,
        )
        self.assertEqual(self.balance(self.kasa), Decimal("40.00"))

    def edit(self, **changes):
        data = {
            "book": self.book.pk, "currency": self.usd.pk,
            "member": self.member.pk, "cash_account": self.kasa.pk,
            "amount": "60.00", "date": "2026-09-22", "exchange_rate": "",
            "description": "September draw",
        }
        data.update(changes)
        return self.client.post(self.url("edit_equity_dividend", self.dividend), data)

    def test_the_detail_page_names_the_member(self):
        response = self.client.get(self.url("equity_dividend_detail", self.dividend))
        self.assertContains(response, str(self.member))
        self.assertContains(response, "September draw")

    def test_the_edit_page_opens_on_the_stored_date(self):
        response = self.client.get(self.url("edit_equity_dividend", self.dividend))
        self.assertContains(response, 'value="2026-09-22"')

    def test_editing_the_amount_reposts_it(self):
        self.edit(amount="90.00")
        self.assertEqual(self.balance(self.kasa), Decimal("10.00"))
        self.assertEqual(list(self.entries(self.dividend).values_list("amount", flat=True)),
                         [Decimal("90.00")])

    def test_an_edit_the_account_cannot_cover_is_refused(self):
        response = self.edit(amount="150.00")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(self.kasa), Decimal("40.00"))
        self.assertEqual(list(self.entries(self.dividend).values_list("amount", flat=True)),
                         [Decimal("60.00")])

    def test_delete_puts_the_cash_back(self):
        self.client.post(self.url("delete_equity_dividend", self.dividend))
        self.assertFalse(EquityDivident.objects.exists())
        self.assertFalse(self.entries(self.dividend).exists())
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))


class InTransferPageTests(CashSourceFixture):
    """70 USD from Cash to Vault."""

    def setUp(self):
        super().setUp()
        self.client.post(
            reverse("accounting:make_in_transfer", kwargs={"pk": self.book.pk}),
            {"mode": "cash", "book": self.book.pk, "currency": self.usd.pk,
             "from_cash_account": self.kasa.pk, "to_cash_account": self.vault.pk,
             "amount": "70.00", "date": "2026-09-23", "description": "to the safe"},
        )
        self.transfer = InTransfer.objects.get()
        self.assertEqual(self.balance(self.kasa), Decimal("30.00"))
        self.assertEqual(self.balance(self.vault), Decimal("70.00"))

    def edit(self, **changes):
        data = {
            "book": self.book.pk, "currency": self.usd.pk,
            "from_cash_account": self.kasa.pk, "to_cash_account": self.vault.pk,
            "amount": "70.00", "date": "2026-09-23", "description": "to the safe",
        }
        data.update(changes)
        return self.client.post(self.url("edit_equity_transfer", self.transfer), data)

    def test_the_detail_page_shows_both_legs(self):
        response = self.client.get(self.url("equity_transfer_detail", self.transfer))
        self.assertContains(response, "to the safe")
        self.assertEqual(len(response.context["cash_entries"]), 2)

    def test_the_detail_page_offers_another_transfer(self):
        response = self.client.get(self.url("equity_transfer_detail", self.transfer))
        self.assertContains(response, 'href="%s"' % reverse(
            "accounting:make_in_transfer", kwargs={"pk": self.book.pk}))

    def test_the_transactions_row_opens_the_transfer(self):
        response = self.client.get(reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        ))
        self.assertContains(
            response, f'data-href="{self.url("equity_transfer_detail", self.transfer)}"'
        )

    def test_editing_the_amount_moves_both_legs(self):
        self.edit(amount="20.00")
        self.assertEqual(self.balance(self.kasa), Decimal("80.00"))
        self.assertEqual(self.balance(self.vault), Decimal("20.00"))

    def test_reversing_the_direction_is_allowed_when_covered(self):
        self.edit(from_cash_account=self.vault.pk, to_cash_account=self.kasa.pk,
                  amount="0.00")
        # Nothing moved either way: both back to where they started.
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))
        self.assertEqual(self.balance(self.vault), Decimal("0.00"))

    def test_delete_is_refused_once_the_vault_is_spent(self):
        CashAccount.objects.filter(pk=self.vault.pk).update(balance=Decimal("10.00"))
        self.client.post(self.url("delete_equity_transfer", self.transfer))
        self.assertTrue(InTransfer.objects.exists())
        self.assertEqual(self.balance(self.vault), Decimal("10.00"))

    def test_delete_puts_both_accounts_back(self):
        self.client.post(self.url("delete_equity_transfer", self.transfer))
        self.assertFalse(InTransfer.objects.exists())
        self.assertFalse(self.entries(self.transfer).exists())
        self.assertEqual(self.balance(self.kasa), Decimal("100.00"))
        self.assertEqual(self.balance(self.vault), Decimal("0.00"))
