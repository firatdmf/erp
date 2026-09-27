# to run this test, use the command:
# python manage.py test accounting.test_payment_form_defaults

import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CurrentAccount


class PaymentFormDefaultsTest(TestCase):
    """The new-payment form's method and cash account defaults."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pay_tester", password="pw"
        )
        self.client.force_login(self.user)

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.user.member.books.add(self.book)

        self.cash_usd = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd
        )
        self.cash_try = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.try_
        )
        self.current_account = CurrentAccount.objects.create(
            book=self.book, code="TST-001", name="Maria", type="customer",
            default_currency=self.usd,
        )

    def url(self):
        return reverse("accounts:payment_create", kwargs={"book_id": self.book.pk}) + "?account=%d" % self.current_account.pk

    def method_options(self, html):
        block = re.search(r'<select name="method"[^>]*>(.*?)</select>', html, re.S).group(1)
        return re.findall(r'<option value="([^"]+)"([^>]*)>', block)

    def test_method_defaults_to_cash(self):
        html = self.client.get(self.url()).content.decode()
        selected = [v for v, attrs in self.method_options(html) if "selected" in attrs]
        self.assertEqual(selected, ["cash"])

    def test_bank_transfer_is_still_offered_just_not_the_default(self):
        """We may add a bank later — the option must stay available."""
        html = self.client.get(self.url()).content.decode()
        values = [v for v, _ in self.method_options(html)]
        self.assertIn("bank_transfer", values)

    def test_each_cash_account_option_carries_its_currency(self):
        """The list narrows to the chosen currency client-side, which
        needs the currency on every option."""
        html = self.client.get(self.url()).content.decode()
        block = re.search(
            r'<select name="cash_account"[^>]*>(.*?)</select>', html, re.S
        ).group(1)
        self.assertIn('data-currency="%d"' % self.usd.pk, block)
        self.assertIn('data-currency="%d"' % self.try_.pk, block)
        for account in (self.cash_usd, self.cash_try):
            self.assertIn('value="%d"' % account.pk, block)

    def test_cash_accounts_are_scoped_to_the_current_account_book(self):
        other = Book.objects.create(name="Başka Defter")
        stranger = CashAccount.objects.create(
            book=other, name="Cash", currency=self.usd
        )
        html = self.client.get(self.url()).content.decode()
        block = re.search(
            r'<select name="cash_account"[^>]*>(.*?)</select>', html, re.S
        ).group(1)
        self.assertNotIn('value="%d"' % stranger.pk, block)


class PaymentFormTypeTest(TestCase):
    """Which payment type the form opens on, given who the account is.

    The account page's two buttons only say which way the money moves.
    Money going out to a customer is a refund to them, not a payment to a
    supplier; money coming in from a supplier is a refund from them.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pay_type_tester", password="pw"
        )
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.user.member.books.add(self.book)

    def account(self, kind):
        return CurrentAccount.objects.create(
            book=self.book, code="TST-%s" % kind, name=kind, type=kind,
            default_currency=self.usd,
        )

    def selected_type(self, account, requested):
        url = reverse("accounts:payment_create", kwargs={"book_id": self.book.pk})
        html = self.client.get(url + "?account=%d&type=%s" % (account.pk, requested)).content.decode()
        block = re.search(r'<select name="type"[^>]*>(.*?)</select>', html, re.S).group(1)
        return [v for v, attrs in re.findall(r'<option value="([^"]+)"([^>]*)>', block) if "selected" in attrs]

    def test_money_out_to_a_customer_is_a_refund(self):
        self.assertEqual(self.selected_type(self.account("customer"), "payment"), ["refund_in"])

    def test_money_in_from_a_customer_is_a_collection(self):
        self.assertEqual(self.selected_type(self.account("customer"), "collection"), ["collection"])

    def test_money_in_from_a_supplier_is_a_refund(self):
        self.assertEqual(self.selected_type(self.account("supplier"), "collection"), ["refund_out"])

    def test_money_out_to_a_supplier_is_a_payment(self):
        self.assertEqual(self.selected_type(self.account("supplier"), "payment"), ["payment"])

    def test_an_account_that_is_both_keeps_the_plain_type(self):
        both = self.account("both")
        self.assertEqual(self.selected_type(both, "payment"), ["payment"])
        self.assertEqual(self.selected_type(both, "collection"), ["collection"])

    def test_an_explicit_refund_type_is_kept(self):
        self.assertEqual(self.selected_type(self.account("customer"), "refund_in"), ["refund_in"])
