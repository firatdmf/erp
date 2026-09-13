# to run this test, use the command:
# python manage.py test accounting.test_cash_accounts

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CurrencyCategory,
    EquityExpense,
    ExpenseCategory,
)


class CashAccountTestBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cash_tester", password="pw"
        )
        self.client.force_login(self.user)

        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")

        self.book = Book.objects.create(name="Demfirat")
        self.other_book = Book.objects.create(name="Nejum")

        self.kasa = CashAccount.objects.create(
            book=self.book, name="Ziraat", currency=self.try_, balance=Decimal("12500.00")
        )
        self.usd_kasa = CashAccount.objects.create(
            book=self.book, name="Garanti", currency=self.usd, balance=Decimal("0.00")
        )
        self.foreign = CashAccount.objects.create(
            book=self.other_book, name="Yapı Kredi", currency=self.try_, balance=Decimal("900.00")
        )

    def detail_url(self, book=None):
        return reverse("accounting:book_detail", kwargs={"pk": (book or self.book).pk})

    def add_url(self, book=None):
        return reverse(
            "accounting:add_cash_account", kwargs={"pk": (book or self.book).pk}
        )

    def edit_url(self, account=None, book=None):
        return reverse(
            "accounting:edit_cash_account",
            kwargs={"pk": (book or self.book).pk, "account_pk": (account or self.kasa).pk},
        )


class CashAccountModelTest(CashAccountTestBase):
    """The FKs carry no default, so a caller that forgets one fails
    loudly instead of quietly attaching the account to book 1."""

    def test_book_is_required(self):
        with self.assertRaises(ValidationError) as ctx:
            CashAccount.objects.create(name="Kasa", currency=self.try_)
        self.assertIn("book", ctx.exception.message_dict)

    def test_currency_is_required(self):
        with self.assertRaises(ValidationError) as ctx:
            CashAccount.objects.create(name="Kasa", book=self.book)
        self.assertIn("currency", ctx.exception.message_dict)


class CashAccountListingTest(CashAccountTestBase):
    """The Cash Accounts card on the book detail page.

    The card reports balances and nothing else. The book page became a
    report — the add and edit affordances moved into the Accounting menu
    (accounting:go_add_cash_account), so the assertions below check the
    figures are right and that the page no longer offers to change them.
    """

    def test_book_detail_lists_only_this_books_accounts(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        listed = list(response.context["cash_accounts"])
        self.assertEqual(listed, [self.kasa, self.usd_kasa])
        self.assertNotIn(self.foreign, listed)

    def test_card_renders_names_and_balances(self):
        html = self.client.get(self.detail_url()).content.decode()
        self.assertIn("Ziraat", html)
        self.assertIn("₺12,500.00", html)
        self.assertNotIn("Yapı Kredi", html)

    def test_card_does_not_offer_to_edit_an_account(self):
        """The page reports the position; it does not change it."""
        html = self.client.get(self.detail_url()).content.decode()
        self.assertNotIn(self.edit_url(), html)

    def test_book_with_no_accounts_says_so(self):
        empty = Book.objects.create(name="Boş Defter")
        response = self.client.get(self.detail_url(empty))
        self.assertEqual(list(response.context["cash_accounts"]), [])
        self.assertIn("no cash accounts yet", response.content.decode())

    def test_card_does_not_offer_to_add_an_account(self):
        """Creating one is a menu action now, not a button on the report."""
        html = self.client.get(self.detail_url()).content.decode()
        self.assertNotIn(self.add_url(), html)


class CashAccountCreateTest(CashAccountTestBase):
    """Creating an account from the book's Cash Accounts card."""

    def test_create_assigns_the_account_to_the_book_it_was_created_from(self):
        """Whichever book's page you start from, the account is that
        book's — for every book, not one special case."""
        books = [self.book, self.other_book] + [
            Book.objects.create(name="Defter %d" % i) for i in range(3)
        ]
        for i, book in enumerate(books):
            self.client.post(
                self.add_url(book), {"name": "Kasa %d" % i, "currency": self.try_.pk}
            )
        for i, book in enumerate(books):
            self.assertEqual(CashAccount.objects.get(name="Kasa %d" % i).book, book)

    def test_new_account_starts_at_zero(self):
        """Balance is a running total of transactions, so a new account
        has nothing to show until one is recorded."""
        self.client.post(self.add_url(), {"name": "Akbank", "currency": self.try_.pk})
        self.assertEqual(CashAccount.objects.get(name="Akbank").balance, Decimal("0.00"))

    def test_posted_balance_is_ignored(self):
        self.client.post(
            self.add_url(),
            {"name": "Akbank", "currency": self.try_.pk, "balance": "50000.00"},
        )
        self.assertEqual(CashAccount.objects.get(name="Akbank").balance, Decimal("0.00"))

    def test_posted_book_is_ignored(self):
        """The URL decides the book, not the payload — posting a
        different book id must not move the account."""
        self.client.post(
            self.add_url(self.other_book),
            {"name": "Akbank", "currency": self.try_.pk, "book": self.book.pk},
        )
        self.assertEqual(CashAccount.objects.get(name="Akbank").book, self.other_book)

    def test_duplicate_name_and_currency_is_rejected(self):
        response = self.client.post(
            self.add_url(), {"name": "Ziraat", "currency": self.try_.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertEqual(CashAccount.objects.filter(name="Ziraat").count(), 1)

    def test_same_name_on_another_book_is_fine(self):
        response = self.client.post(
            self.add_url(self.other_book), {"name": "Ziraat", "currency": self.try_.pk}
        )
        self.assertRedirects(response, self.detail_url(self.other_book))
        self.assertEqual(
            CashAccount.objects.filter(name="Ziraat", book=self.other_book).count(), 1
        )

    def test_currency_is_selectable_on_a_new_account(self):
        response = self.client.get(self.add_url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].fields["currency"].disabled)

    def test_unknown_book_is_a_404(self):
        response = self.client.get(
            reverse("accounting:add_cash_account", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.add_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])


class CashAccountEditTest(CashAccountTestBase):
    """Editing an account through its book."""

    def test_rename_saves(self):
        response = self.client.post(
            self.edit_url(), {"name": "Ziraat Bankası", "currency": self.try_.pk}
        )
        self.assertRedirects(response, self.detail_url())
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.name, "Ziraat Bankası")

    def test_balance_is_not_editable(self):
        """The balance is a running total of the account's transactions —
        the form must not offer a way to overwrite it."""
        response = self.client.get(self.edit_url())
        self.assertNotIn("balance", response.context["form"].fields)
        self.client.post(
            self.edit_url(),
            {"name": "Ziraat", "currency": self.try_.pk, "balance": "999999.00"},
        )
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("12500.00"))

    def test_book_cannot_be_reassigned(self):
        response = self.client.get(self.edit_url())
        self.assertNotIn("book", response.context["form"].fields)
        self.client.post(
            self.edit_url(),
            {"name": "Ziraat", "currency": self.try_.pk, "book": self.other_book.pk},
        )
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.book, self.book)

    def test_currency_is_editable_while_the_account_is_unused(self):
        response = self.client.get(self.edit_url(self.usd_kasa))
        self.assertFalse(response.context["form"].fields["currency"].disabled)
        self.client.post(
            self.edit_url(self.usd_kasa), {"name": "Garanti", "currency": self.try_.pk}
        )
        self.usd_kasa.refresh_from_db()
        self.assertEqual(self.usd_kasa.currency, self.try_)

    def test_currency_locks_once_the_account_has_activity(self):
        """Balances are summed per currency across the book, so
        re-denominating a used account would restate its totals."""
        EquityExpense.objects.create(
            book=self.book,
            category=ExpenseCategory.objects.create(name="Kira"),
            cash_account=self.usd_kasa,
            currency=self.usd,
            amount=Decimal("100.00"),
            date="2026-08-01",
        )
        self.assertTrue(self.usd_kasa.is_in_use)

        response = self.client.get(self.edit_url(self.usd_kasa))
        self.assertTrue(response.context["form"].fields["currency"].disabled)

        self.client.post(
            self.edit_url(self.usd_kasa), {"name": "Garanti", "currency": self.try_.pk}
        )
        self.usd_kasa.refresh_from_db()
        self.assertEqual(self.usd_kasa.currency, self.usd)

    def test_duplicate_name_and_currency_in_the_same_book_is_rejected(self):
        CashAccount.objects.create(
            book=self.book, name="Vakıf", currency=self.try_, balance=Decimal("0.00")
        )
        response = self.client.post(
            self.edit_url(), {"name": "Vakıf", "currency": self.try_.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.name, "Ziraat")

    def test_same_name_in_another_currency_is_fine(self):
        response = self.client.post(
            self.edit_url(self.usd_kasa), {"name": "Ziraat", "currency": self.usd.pk}
        )
        self.assertRedirects(response, self.detail_url())
        self.usd_kasa.refresh_from_db()
        self.assertEqual(self.usd_kasa.name, "Ziraat")

    def test_another_books_account_is_not_reachable(self):
        response = self.client.get(self.edit_url(self.foreign))
        self.assertEqual(response.status_code, 404)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.edit_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])
