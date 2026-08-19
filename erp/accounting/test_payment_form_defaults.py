# to run this test, use the command:
# python manage.py test accounting.test_payment_form_defaults

import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CariAccount


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

        self.cash_usd = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd
        )
        self.cash_try = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.try_
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Maria", type="customer",
            default_currency=self.usd,
        )

    def url(self):
        return reverse("accounts:payment_create") + "?account=%d" % self.cari.pk

    def method_options(self, html):
        block = re.search(r'<select name="method">(.*?)</select>', html, re.S).group(1)
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

    def test_cash_accounts_are_scoped_to_the_cari_book(self):
        other = Book.objects.create(name="Başka Defter")
        stranger = CashAccount.objects.create(
            book=other, name="Cash", currency=self.usd
        )
        html = self.client.get(self.url()).content.decode()
        block = re.search(
            r'<select name="cash_account"[^>]*>(.*?)</select>', html, re.S
        ).group(1)
        self.assertNotIn('value="%d"' % stranger.pk, block)
