# to run this test, use the command:
# python manage.py test operating.tests.test_customer_currency_notice

"""The order form says what the order will be priced in.

An order is kept in its customer's own currency. The form has to say so the
moment a customer is picked — and say it loudly when that is not the book's
own currency, because a price typed in euros and read as dollars is exactly
how order 303 went wrong.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact


class CustomerCurrencyTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.euroland = Company.objects.create(name="Euroland")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-EUR", name="Euroland", type="customer",
            company=self.euroland, default_currency=self.eur)
        self.dollarland = Company.objects.create(name="Dollarland")
        CurrentAccount.objects.create(
            book=self.book, code="C-USD", name="Dollarland", type="customer",
            company=self.dollarland, default_currency=self.usd)
        self.stranger = Contact.objects.create(name="Nobody Yet")

        user = get_user_model().objects.create_superuser("firat_cc", "a@b.c", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _ask(self, customer, kind="company"):
        return self.client.get(reverse("operating:customer_currency"),
                               {"book": self.book.pk, "type": kind, "pk": customer.pk})

    def test_a_foreign_customer_is_named_as_such(self):
        d = self._ask(self.euroland).json()
        self.assertEqual(d["currency"], "EUR")
        self.assertEqual(d["symbol"], "€")
        self.assertEqual(d["account"], "Euroland")
        self.assertFalse(d["is_base"])
        self.assertEqual(d["base"], "USD")

    def test_a_customer_in_the_books_own_currency_needs_no_warning(self):
        d = self._ask(self.dollarland).json()
        self.assertEqual(d["currency"], "USD")
        self.assertTrue(d["is_base"])

    def test_a_customer_with_no_account_yet_gets_the_default(self):
        d = self._ask(self.stranger, kind="contact").json()
        self.assertEqual(d["currency"], "USD")
        self.assertIsNone(d["account"])

    def test_an_unknown_customer_is_refused(self):
        r = self.client.get(reverse("operating:customer_currency"),
                            {"book": self.book.pk, "type": "company", "pk": 999999})
        self.assertEqual(r.status_code, 404)

    def test_the_form_carries_the_books_currency_and_the_lookup(self):
        r = self.client.get(reverse("operating:create_order"),
                            HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["base_currency_symbol"], "$")
        self.assertContains(r, "co-currency-note")
        self.assertContains(r, reverse("operating:customer_currency"))
