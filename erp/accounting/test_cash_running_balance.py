# to run this test, use the command:
# python manage.py test accounting.test_cash_running_balance

from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    EquityCapital,
    EquityExpense,
    ExpenseCategory,
)
from django.contrib.auth import get_user_model


class CashEntryTestBase(TestCase):
    """Shared fixture: one book, one USD kasa, and a way to move money.

    Everything here stays in the base currency (USD) so no FX rate is
    fetched — the drift being tested has nothing to do with conversion.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )[0]
        self.book = Book.objects.create(name="Laleli Fabric")
        self.kasa = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("0.00")
        )
        # A Member is created for every user by signal — take that one.
        user = get_user_model().objects.create_user(username="teller", password="pw")
        self.member = user.member

    def _entry(self, amount, positive):
        """Move the cash account, then record the entry — the caller's order.

        Moved with an F() UPDATE rather than instance.save() so the helper
        neither clobbers a balance changed behind its back nor trips
        CashAccount.clean()'s no-negative rule, which the real cash-moving
        paths (Payment.post) also bypass.
        """
        delta = Decimal(amount) if positive else -Decimal(amount)
        CashAccount.objects.filter(pk=self.kasa.pk).update(
            balance=models.F("balance") + delta
        )
        self.kasa.refresh_from_db()
        # content_* just needs to point at something real; the running total
        # is not derived from it.
        capital = EquityCapital.objects.create(
            book=self.book,
            member=self.member,
            date_invested="2026-08-19",
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal(amount),
        )
        return CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=capital.pk,
            amount=Decimal(amount),
            is_amount_positive=positive,
            currency=self.usd,
            cash_account=self.kasa,
        )


class CashRunningBalanceTests(CashEntryTestBase):
    """Running balances are worked out from the rows, not stamped onto them.

    Derived, so they cannot describe a past that later edits changed. These
    assert on views.running_cash_balances rather than on any stored column.
    """

    def _balances(self):
        from accounting.views import running_cash_balances

        return running_cash_balances(self.book.pk)

    def _entry_dated(self, amount, positive, date):
        """An entry whose source carries `date`, so it sorts by it."""
        delta = Decimal(amount) if positive else -Decimal(amount)
        CashAccount.objects.filter(pk=self.kasa.pk).update(
            balance=models.F("balance") + delta
        )
        self.kasa.refresh_from_db()
        capital = EquityCapital.objects.create(
            book=self.book, member=self.member, date_invested=date,
            cash_account=self.kasa, currency=self.usd, amount=Decimal(amount),
        )
        return CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=capital.pk,
            amount=Decimal(amount),
            is_amount_positive=positive,
            currency=self.usd,
            cash_account=self.kasa,
        )

    def test_the_running_total_accumulates_down_the_ledger(self):
        first = self._entry("600.00", True)
        second = self._entry("100.00", False)

        balances = self._balances()
        self.assertEqual(balances[first.pk], (Decimal("600.00"), Decimal("600.00")))
        self.assertEqual(balances[second.pk], (Decimal("500.00"), Decimal("500.00")))

    def test_the_ledger_ends_where_the_cash_account_stands(self):
        """The invariant: sum the entries, get the account."""
        self._entry("600.00", True)
        last = self._entry("100.00", False)

        self.kasa.refresh_from_db()
        self.assertEqual(self._balances()[last.pk][0], self.kasa.balance)

    def test_a_backdated_row_sorts_into_the_middle_and_totals_follow(self):
        """What a stored running balance could not do without a repair run."""
        early = self._entry_dated("100.00", True, "2026-08-10")
        late = self._entry_dated("200.00", True, "2026-08-20")
        # Entered last, but it happened between the two.
        middle = self._entry_dated("50.00", True, "2026-08-15")

        balances = self._balances()
        self.assertEqual(balances[early.pk][1], Decimal("100.00"))
        self.assertEqual(balances[middle.pk][1], Decimal("150.00"))
        self.assertEqual(balances[late.pk][1], Decimal("350.00"))

    def test_editing_an_amount_moves_every_total_after_it(self):
        """No repair command in between — the figures are derived."""
        first = self._entry_dated("100.00", True, "2026-08-10")
        second = self._entry_dated("200.00", True, "2026-08-20")
        self.assertEqual(self._balances()[second.pk][1], Decimal("300.00"))

        first.amount = Decimal("500.00")
        first.amount_in_base_currency = None  # reconvert on purpose
        first.save()

        self.assertEqual(self._balances()[second.pk][1], Decimal("700.00"))

    def test_a_negative_total_is_not_flattened_to_zero(self):
        """The old stored column clamped anything under a cent to 0.00."""
        entry = self._entry("100.00", False)
        self.assertEqual(self._balances()[entry.pk][1], Decimal("-100.00"))

    def test_each_account_runs_its_own_balance(self):
        vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        kasa_row = self._entry("600.00", True)
        capital = EquityCapital.objects.first()
        vault_row = CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=capital.pk,
            amount=Decimal("25.00"),
            is_amount_positive=True,
            currency=self.usd,
            cash_account=vault,
        )

        balances = self._balances()
        # Each account's own running balance, but one shared book total.
        self.assertEqual(balances[kasa_row.pk][0], Decimal("600.00"))
        self.assertEqual(balances[vault_row.pk][0], Decimal("25.00"))
        self.assertEqual(balances[vault_row.pk][1], Decimal("625.00"))


class CashEntryDateTests(CashEntryTestBase):
    """The entry files under the date the money moved, not the day it was typed."""

    def test_date_comes_from_the_source_not_today(self):
        entry = self._entry("600.00", True)
        # _entry's EquityCapital is dated 19 Aug 2026; the row is created now.
        self.assertEqual(str(entry.date), "2026-08-19")
        self.assertNotEqual(entry.date, entry.created_at.date())

    def test_a_backdated_exchange_keeps_its_own_date(self):
        """The case that started this: entered on the 26th, dated the 21st."""
        from accounting.models import CurrencyExchange

        other = CashAccount.objects.create(
            book=self.book, name="Kasa TRY", currency=self.usd, balance=Decimal("0.00")
        )
        exchange = CurrencyExchange.objects.create(
            book=self.book,
            from_cash_account=self.kasa,
            to_cash_account=other,
            from_amount=Decimal("200.00"),
            to_amount=Decimal("200.00"),
            date="2026-08-21",
        )
        entry = CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(CurrencyExchange),
            content_pk=exchange.pk,
            amount=Decimal("200.00"),
            is_amount_positive=False,
            currency=self.usd,
            cash_account=self.kasa,
        )
        self.assertEqual(str(entry.date), "2026-08-21")

    def test_an_explicit_date_is_not_overwritten(self):
        entry = CashTransactionEntry(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=1,
            amount=Decimal("10.00"),
            is_amount_positive=True,
            currency=self.usd,
            cash_account=self.kasa,
            date="2026-01-05",
        )
        entry.save()
        self.assertEqual(str(entry.date), "2026-01-05")


class CashEntryDateBackfillTests(CashEntryTestBase):
    """Migration 0077's backfill, exercised on real rows.

    The function takes `apps`, so it can be handed the live registry and
    called directly — cheaper than standing up a migration harness, and it
    tests the query shape that actually runs against production.
    """

    @staticmethod
    def _backfill():
        """Call migration 0077's backfill against the live app registry."""
        from importlib import import_module
        from django.apps import apps as registry

        module = import_module(
            "accounting.migrations.0077_cash_transaction_entry_date"
        )
        module.backfill_dates(registry, None)

    def _blank_the_dates(self):
        CashTransactionEntry.objects.update(date=None)

    def test_backfill_fills_every_row_from_its_source(self):
        capital_entry = self._entry("600.00", True)
        self._blank_the_dates()
        self.assertIsNone(
            CashTransactionEntry.objects.get(pk=capital_entry.pk).date
        )

        self._backfill()

        capital_entry.refresh_from_db()
        # EquityCapital keeps its date on date_invested, not date.
        self.assertEqual(str(capital_entry.date), "2026-08-19")

    def test_backfill_is_a_handful_of_queries_not_one_per_row(self):
        """The shape that made the first attempt unusable over the proxy."""
        for _ in range(8):
            self._entry("10.00", True)
        self._blank_the_dates()

        # 8 rows sharing one source model and one date: reading the rows,
        # the content types, the source dates, then a single grouped UPDATE.
        with self.assertNumQueries(4):
            self._backfill()

        self.assertFalse(
            CashTransactionEntry.objects.filter(date__isnull=True).exists()
        )


class CashEntryListPageTests(CashEntryTestBase):
    """The transactions page: descriptions, and filtering by cash account."""

    def setUp(self):
        super().setUp()
        self.client.force_login(get_user_model().objects.get(username="teller"))
        self.other = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )

    def url(self, **params):
        base = reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        )
        return base + ("?" + urlencode(params) if params else "")

    def test_the_description_typed_on_the_source_is_shown(self):
        category = ExpenseCategory.objects.create(name="Contract Labor")
        expense = EquityExpense.objects.create(
            book=self.book,
            category=category,
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal("815.00"),
            date="2026-08-20",
            description="hamal cuval",
        )
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("1000.00"))
        self.kasa.refresh_from_db()
        CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityExpense),
            content_pk=expense.pk,
            amount=Decimal("815.00"),
            is_amount_positive=False,
            currency=self.usd,
            cash_account=self.kasa,
        )

        response = self.client.get(self.url())
        self.assertContains(response, "hamal cuval")

    def test_a_source_with_no_description_still_says_something(self):
        """A capital deposit with a blank note is identified by its member."""
        self._entry("600.00", True)  # note left empty
        response = self.client.get(self.url())
        self.assertContains(response, str(self.member))
        row = response.context["object_list"][0]
        self.assertEqual(row.source_heading, str(self.member))
        self.assertEqual(row.source_description, "")

    def test_filtering_narrows_to_one_cash_account(self):
        self._entry("600.00", True)  # lands in self.kasa
        CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=EquityCapital.objects.first().pk,
            amount=Decimal("25.00"),
            is_amount_positive=True,
            currency=self.usd,
            cash_account=self.other,
        )

        everything = self.client.get(self.url())
        self.assertEqual(len(everything.context["object_list"]), 2)

        just_vault = self.client.get(self.url(account=self.other.pk))
        rows = just_vault.context["object_list"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].cash_account_id, self.other.pk)
        self.assertEqual(just_vault.context["selected_account"], self.other)

    def test_every_cash_account_in_the_book_gets_a_tab_with_its_count(self):
        self._entry("600.00", True)
        response = self.client.get(self.url())
        tabs = {r["account"].name: r["count"] for r in response.context["cash_accounts"]}
        self.assertEqual(tabs, {"Cash": 1, "Vault": 0})
        self.assertEqual(response.context["total_count"], 1)
        self.assertIsNone(response.context["selected_account"])

    def test_an_account_id_from_another_book_matches_nothing(self):
        self._entry("600.00", True)
        stranger = CashAccount.objects.create(
            book=Book.objects.create(name="Nejum"),
            name="Theirs",
            currency=self.usd,
            balance=Decimal("0.00"),
        )
        response = self.client.get(self.url(account=stranger.pk))
        self.assertEqual(len(response.context["object_list"]), 0)
        self.assertIsNone(response.context["selected_account"])

    def test_a_junk_account_parameter_falls_back_to_all(self):
        self._entry("600.00", True)
        response = self.client.get(self.url(account="; drop table"))
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertIsNone(response.context["selected_account"])

    def test_the_page_does_not_query_once_per_row(self):
        """Descriptions come from a GenericForeignKey — the trap is N+1.

        Asserted as "the count does not grow with the rows" rather than a
        fixed number, because base.html's context processors dominate the
        total and would make any literal here a chore to maintain.
        """
        for _ in range(3):
            self._entry("10.00", True)
        with CaptureQueriesContext(connection) as few:
            self.client.get(self.url())

        for _ in range(9):
            self._entry("10.00", True)
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.url())

        self.assertEqual(len(many.captured_queries), len(few.captured_queries))


class CashEntryExchangeDescriptionTests(CashEntryTestBase):
    """An exchange or transfer has no description field; it gets described."""

    def _describe(self, obj):
        from accounting.views import describe_cash_entry_source

        accounts = {
            a.pk: a for a in CashAccount.objects.filter(book=self.book)
        }
        return describe_cash_entry_source(obj, accounts)

    def test_across_currencies_the_symbols_carry_it(self):
        from accounting.models import CurrencyExchange

        try_ = CurrencyCategory.objects.get_or_create(
            code="TRY", defaults={"name": "Turkish Lira", "symbol": "₺"}
        )[0]
        lira = CashAccount.objects.create(
            book=self.book, name="Cash", currency=try_, balance=Decimal("0.00")
        )
        exchange = CurrencyExchange.objects.create(
            book=self.book,
            from_cash_account=self.kasa,
            to_cash_account=lira,
            from_amount=Decimal("200.00"),
            to_amount=Decimal("9560.00"),
            date="2026-08-21",
        )
        self.assertEqual(self._describe(exchange), "$200.00 → ₺9,560.00")

    def test_within_one_currency_the_accounts_are_named(self):
        from accounting.models import InTransfer

        vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        transfer = InTransfer.objects.create(
            book=self.book,
            from_cash_account=self.kasa,
            to_cash_account=vault,
            amount=Decimal("500.00"),
            currency=self.usd,
            date="2026-08-21",
        )
        self.assertEqual(
            self._describe(transfer), "$500.00 Cash → $500.00 Vault"
        )


class CashEntryHeadingTests(CashEntryTestBase):
    """What the row is, shown alongside the note rather than instead of it."""

    def setUp(self):
        super().setUp()
        self.client.force_login(get_user_model().objects.get(username="teller"))

    def url(self):
        return reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        )

    def test_a_described_capital_deposit_still_names_its_member(self):
        """The bug: a typed description used to hide the counterparty."""
        capital = EquityCapital.objects.create(
            book=self.book,
            member=self.member,
            date_invested="2026-08-20",
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal("1000.00"),
            note="dükkanda elden verdi",
        )
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("1000.00"))
        self.kasa.refresh_from_db()
        CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityCapital),
            content_pk=capital.pk,
            amount=Decimal("1000.00"),
            is_amount_positive=True,
            currency=self.usd,
            cash_account=self.kasa,
        )

        row = self.client.get(self.url()).context["object_list"][0]
        self.assertEqual(row.source_heading, str(self.member))
        self.assertEqual(row.source_description, "dükkanda elden verdi")

    def test_an_exchange_has_no_heading(self):
        """Nobody is on the other side of moving your own money."""
        from accounting.models import CurrencyExchange
        from accounting.views import cash_entry_heading

        vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        exchange = CurrencyExchange.objects.create(
            book=self.book,
            from_cash_account=self.kasa,
            to_cash_account=vault,
            from_amount=Decimal("10.00"),
            to_amount=Decimal("10.00"),
            date="2026-08-21",
        )
        self.assertEqual(cash_entry_heading(exchange), "")


class CashEntryHtmxTests(CashEntryTestBase):
    """Filtering swaps a fragment in rather than reloading the page."""

    def setUp(self):
        super().setUp()
        self.client.force_login(get_user_model().objects.get(username="teller"))
        self._entry("600.00", True)

    def url(self):
        return reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        )

    def test_an_htmx_request_returns_only_the_fragment(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertEqual(
            response.template_name,
            ["accounting/partials/cash_transaction_results.html"],
        )
        body = response.content.decode()
        self.assertNotIn("<html", body)
        self.assertIn("tx-filter", body)  # tabs come along, so "on" moves

    def test_an_ordinary_request_still_returns_the_whole_page(self):
        response = self.client.get(self.url())
        self.assertIn(
            "accounting/cash_transaction_entry_list.html", response.template_name
        )
        self.assertIn('id="tx-results"', response.content.decode())

    def test_the_fragment_and_the_page_agree_on_the_rows(self):
        """One definition of the markup — the page includes the partial."""
        page = self.client.get(self.url()).content.decode()
        fragment = self.client.get(
            self.url(), HTTP_HX_REQUEST="true"
        ).content.decode()
        self.assertIn(fragment.strip(), page)


class CashEntryExpenseHeadingTests(CashEntryTestBase):
    """An expense is identified by its category, the way a payment is by its cari."""

    def setUp(self):
        super().setUp()
        self.client.force_login(get_user_model().objects.get(username="teller"))

    def test_the_expense_category_leads_the_cell(self):
        from accounting.views import cash_entry_heading

        expense = EquityExpense.objects.create(
            book=self.book,
            category=ExpenseCategory.objects.create(name="Contract Labor"),
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal("815.00"),
            date="2026-08-20",
            description="hamal cuval",
        )
        self.assertEqual(cash_entry_heading(expense), "Contract Labor")

    def test_an_uncategorised_expense_shows_only_its_description(self):
        from accounting.views import cash_entry_heading

        expense = EquityExpense.objects.create(
            book=self.book,
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal("600.00"),
            date="2026-08-21",
            description="",
        )
        self.assertEqual(cash_entry_heading(expense), "")

    def test_the_page_renders_category_above_description(self):
        expense = EquityExpense.objects.create(
            book=self.book,
            category=ExpenseCategory.objects.create(name="Wages"),
            cash_account=self.kasa,
            currency=self.usd,
            amount=Decimal("600.00"),
            date="2026-08-21",
            description="ustabaşı",
        )
        CashAccount.objects.filter(pk=self.kasa.pk).update(balance=Decimal("1000.00"))
        self.kasa.refresh_from_db()
        CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(EquityExpense),
            content_pk=expense.pk,
            amount=Decimal("600.00"),
            is_amount_positive=False,
            currency=self.usd,
            cash_account=self.kasa,
        )
        url = reverse(
            "accounting:cash_transaction_entry_list", kwargs={"pk": self.book.pk}
        )
        row = self.client.get(url).context["object_list"][0]
        self.assertEqual(row.source_heading, "Wages")
        self.assertEqual(row.source_description, "ustabaşı")
