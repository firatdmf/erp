# to run this test, use the command:
# python manage.py test accounting.test_own_currency_balance

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting import services
from accounting.models import (
    Book, CurrencyCategory, CurrencyExchangeRate, CurrentAccount, CurrentAccountMovement, Payment,
)


class OwnCurrencyBase(TestCase):
    """An account tracked in lira, in a book kept in dollars."""

    def setUp(self):
        # get_exchange_rate memoises per process; a rate another test left
        # behind for the same day would answer instead of this test's row.
        services._RATE_MEMO.clear()
        self.user = get_user_model().objects.create_user(username="own_ccy", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.user.member.books.add(self.book)
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-088", name="ERGUL KARGO", type="supplier",
            default_currency=self.try_)
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="TRY", rate=Decimal("48.495000"), date="2026-09-11")

    def lira(self, amount, rate="0.02062000", **kw):
        amount = Decimal(amount)
        return CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-11",
            amount=amount, currency=self.try_,
            movement_type=kw.pop("movement_type", "adjustment"),
            exchange_rate=Decimal(rate),
            amount_base=(amount * Decimal(rate)).quantize(Decimal("0.01")), **kw)

    def dollars(self, amount, **kw):
        return CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-11",
            amount=Decimal(amount), currency=self.usd, movement_type="payment", **kw)

    def refresh(self):
        return CurrentAccount.objects.select_related("default_currency").get(pk=self.account.pk)


class OwnCurrencyBalanceTest(OwnCurrencyBase):

    def test_a_base_currency_account_has_no_own_balance(self):
        """Its cached_balance already is that figure."""
        self.account.default_currency = self.usd
        self.account.save()
        self.dollars("40.00")
        account = self.refresh()
        self.assertIsNone(account.own_currency)
        self.assertIsNone(account.own_currency_balance())

    def test_lira_rows_count_for_the_lira_on_them(self):
        """Whatever rate they converted to dollars at — a lira-only supplier
        must not owe a different sum when the rate moves."""
        self.lira("-4210.00", rate="0.02062000")
        self.lira("2000.00", rate="0.03000000")
        self.assertEqual(self.refresh().own_currency_balance(), Decimal("-2210.00"))

    def test_a_dollar_row_converts_at_the_rate_on_its_own_date(self):
        self.lira("-4210.00")
        self.lira("2000.00")
        self.dollars("40.00")
        account = self.refresh()
        # 40 × 48.495 = 1,939.80
        self.assertEqual(account.own_currency_balance(), Decimal("-270.20"))
        self.assertEqual(account.cached_balance, Decimal("-5.57"))

    def test_a_voided_row_is_left_out_as_the_base_balance_leaves_it_out(self):
        self.lira("-4210.00")
        self.lira("-1000.00", is_void=True)
        self.assertEqual(self.refresh().own_currency_balance(), Decimal("-4210.00"))

    def test_no_rate_means_no_own_balance_rather_than_a_partial_one(self):
        self.lira("-4210.00")
        self.dollars("40.00")
        account = self.refresh()
        with mock.patch("accounting.services.get_exchange_rate", return_value=None):
            self.assertIsNone(account.own_currency_balance())


class AccountPageTest(OwnCurrencyBase):

    def page(self):
        response = self.client.get(reverse("accounts:detail", args=[self.account.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_balance_reads_in_the_accounts_currency(self):
        self.lira("-4210.00")
        self.lira("2000.00")
        self.dollars("40.00")
        response = self.page()
        self.assertContains(response, "₺270.20")
        self.assertNotContains(response, "$5.57")
        self.assertEqual(response.context["own_balance_label"], "We Owe")

    def test_the_running_column_walks_back_in_lira(self):
        self.lira("-4210.00")
        self.lira("2000.00")
        self.dollars("40.00")
        rows = self.page().context["movements"]
        self.assertEqual([r["balance_after"] for r in rows],
                         [Decimal("-270.20"), Decimal("-2210.00"), Decimal("-4210.00")])

    def test_only_a_row_in_another_currency_states_a_rate(self):
        """Toward the account's currency — the mirror of a lira row on a
        dollar account — and nothing on a row that converted nothing."""
        self.lira("-4210.00")
        self.dollars("40.00")
        response = self.page()
        self.assertContains(response, '<span class="cd-fx">₺1,939.80 @ 48.495</span>', html=False)
        self.assertNotContains(response, "@ 0.02062")
        self.assertEqual(response.content.decode().count('<span class="cd-fx">'), 1)

    def test_a_dollar_account_is_unchanged(self):
        self.account.default_currency = self.usd
        self.account.save()
        # A lira row on a dollar account can only be a settling type.
        self.lira("-4210.00", movement_type="advance_in")
        response = self.page()
        self.assertContains(response, "$86.81")
        self.assertContains(response, "@ 0.02062")
        self.assertIsNone(response.context["own_balance"])

    def test_without_a_rate_the_page_falls_back_to_dollars(self):
        """A whole page in one currency, not a lira column with a gap."""
        self.lira("-4210.00")
        self.dollars("40.00")
        with mock.patch("accounting.services.get_exchange_rate", return_value=None):
            response = self.page()
        self.assertIsNone(response.context["own_balance"])
        self.assertContains(response, "$46.81")
        self.assertContains(response, "@ 0.02062")


class PaymentRateTowardAccountTest(OwnCurrencyBase):
    """On a lira account, the payment form's rate converts a dollar payment
    into lira — the mirror of a lira payment on a dollar account."""

    def create_url(self):
        return reverse("accounts:payment_create", kwargs={"book_id": self.book.pk})

    def edit_url(self, payment):
        return reverse("accounts:payment_edit", kwargs={"pk": payment.pk})

    def post_payment(self, url=None, **overrides):
        data = {
            "account": self.account.pk, "type": "payment", "method": "cash",
            "date": "2026-09-11", "amount": "40.00", "currency": self.usd.pk,
            "description": "", "notes": "", "allocations_json": "[]",
            "auto_confirm": "1", "exchange_rate": "48.600000",
        }
        data.update(overrides)
        return self.client.post(url or self.create_url(), data)

    # -- the form ----------------------------------------------------------
    def test_the_form_tells_the_script_the_accounts_currency(self):
        response = self.client.get(self.create_url(), {"account": self.account.pk})
        self.assertContains(response, 'var ACCOUNT = {"id": %d, "code": "TRY"' % self.try_.pk)

    def test_a_dollar_account_gives_the_script_none(self):
        """So the box goes on converting toward the book, as it always has."""
        self.account.default_currency = self.usd
        self.account.save()
        response = self.client.get(self.create_url(), {"account": self.account.pk})
        self.assertContains(response, "var ACCOUNT = null;")

    def test_the_edit_form_shows_the_saved_rate(self):
        self.post_payment()
        response = self.client.get(self.edit_url(Payment.objects.get()))
        self.assertContains(response, 'value="48.600000"')

    # -- what gets saved ---------------------------------------------------
    def test_a_rate_typed_for_a_dollar_payment_is_toward_the_account(self):
        self.post_payment()
        payment = Payment.objects.get()
        self.assertEqual(payment.status, "confirmed")
        self.assertEqual(payment.account_exchange_rate, Decimal("48.600000"))
        self.assertIsNone(payment.exchange_rate)
        movement = payment.posted_movement
        self.assertEqual(movement.account_rate, Decimal("48.600000"))
        # The book still holds forty dollars.
        self.assertEqual(movement.amount_base, Decimal("40.00"))
        self.assertEqual(self.refresh().own_currency_balance(), Decimal("1944.00"))

    def test_an_empty_box_leaves_the_published_rate_to_apply(self):
        self.post_payment(exchange_rate="")
        self.assertIsNone(Payment.objects.get().posted_movement.account_rate)
        # 40 × the published 48.495
        self.assertEqual(self.refresh().own_currency_balance(), Decimal("1939.80"))

    def test_a_lira_payment_still_states_its_rate_toward_the_book(self):
        """It is in the account's currency, but the book needs it in dollars."""
        self.post_payment(currency=self.try_.pk, amount="2000.00", exchange_rate="0.020620")
        payment = Payment.objects.get()
        self.assertEqual(payment.exchange_rate, Decimal("0.020620"))
        self.assertIsNone(payment.account_exchange_rate)
        self.assertIsNone(payment.posted_movement.account_rate)
        self.assertEqual(payment.posted_movement.amount_base, Decimal("41.24"))

    def test_editing_the_rate_reconverts_the_account_side(self):
        self.post_payment()
        payment = Payment.objects.get()
        self.post_payment(url=self.edit_url(payment), exchange_rate="50.000000")
        self.assertEqual(self.refresh().own_currency_balance(), Decimal("2000.00"))

    def test_switching_to_lira_drops_the_rate_meant_for_dollars(self):
        self.post_payment()
        payment = Payment.objects.get()
        self.post_payment(url=self.edit_url(payment), currency=self.try_.pk,
                          amount="2000.00", exchange_rate="0.020620")
        payment.refresh_from_db()
        self.assertIsNone(payment.account_exchange_rate)
        self.assertEqual(payment.exchange_rate, Decimal("0.020620"))
        payment.posted_movement.refresh_from_db()
        self.assertIsNone(payment.posted_movement.account_rate)

    # -- the pages that show it ---------------------------------------------
    def test_the_payment_page_states_the_rate_into_lira(self):
        self.post_payment()
        response = self.client.get(
            reverse("accounts:payment_detail", kwargs={"pk": Payment.objects.get().pk}))
        self.assertContains(response, "1 USD = 48.60 TRY")
        self.assertContains(response, "Value in TRY")
        self.assertContains(response, "1,944.00")

    def test_the_account_page_moves_by_the_typed_rate(self):
        self.post_payment()
        response = self.client.get(reverse("accounts:detail", args=[self.account.pk]))
        self.assertContains(response, "₺1,944.00 @ 48.60")
        self.assertContains(response, "₺1,944.00")
