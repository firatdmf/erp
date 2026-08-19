# to run this test, use the command:
# python manage.py test accounting.test_expense_list

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CurrencyCategory,
    EquityExpense,
    ExpenseCategory,
)


class EquityExpenseListTest(TestCase):
    """The book's expense page — reached from Book Detail → View Expenses."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="expense_tester", password="pw"
        )
        self.client.force_login(self.user)

        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")

        self.book = Book.objects.create(name="Demfirat")
        self.other_book = Book.objects.create(name="Nejum")

        self.kasa = CashAccount.objects.create(
            book=self.book, name="Ziraat TRY", currency=self.try_, balance=Decimal("100000.00")
        )
        self.other_kasa = CashAccount.objects.create(
            book=self.other_book, name="Garanti USD", currency=self.usd, balance=Decimal("5000.00")
        )

        self.rent = ExpenseCategory.objects.create(name="Kira")

        # Two on our book, deliberately entered out of date order so the
        # newest-first ordering has something to actually do.
        self.older = EquityExpense.objects.create(
            book=self.book, category=self.rent, cash_account=self.kasa,
            currency=self.try_, amount=Decimal("12500.00"),
            date="2026-07-01", description="Temmuz ofis kirası",
        )
        self.newer = EquityExpense.objects.create(
            book=self.book, category=self.rent, cash_account=self.kasa,
            currency=self.try_, amount=Decimal("12500.00"),
            date="2026-08-01", description="Ağustos ofis kirası",
        )
        # A third on a DIFFERENT book — this one must never show up.
        self.foreign = EquityExpense.objects.create(
            book=self.other_book, category=None, cash_account=self.other_kasa,
            currency=self.usd, amount=Decimal("340.50"),
            date="2026-08-03", description="Sunucu kirası",
        )

    def url(self, book):
        return reverse("accounting:equity_expense_list", kwargs={"pk": book.pk})

    def test_page_renders(self):
        """The template exists — this is the bug the page shipped with."""
        response = self.client.get(self.url(self.book))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounting/equity_expense_list.html")

    def test_only_this_books_expenses_are_listed(self):
        response = self.client.get(self.url(self.book))
        listed = list(response.context["object_list"])
        self.assertEqual(listed, [self.newer, self.older])
        self.assertNotIn(self.foreign, listed)

    def test_other_book_sees_only_its_own(self):
        response = self.client.get(self.url(self.other_book))
        self.assertEqual(list(response.context["object_list"]), [self.foreign])

    def test_rows_render_their_values(self):
        response = self.client.get(self.url(self.book))
        html = response.content.decode()
        self.assertIn("Ağustos ofis kirası", html)
        self.assertIn("Kira", html)
        self.assertIn("Ziraat TRY", html)
        # Accounts are named for the place, not the currency ("Cash"), so
        # the code has to be printed beside the name to tell them apart.
        self.assertIn('<span class="ccy">TRY</span>', html)
        # Amounts are thousands-separated, not raw decimals.
        self.assertIn("₺12,500.00", html)
        self.assertNotIn("Sunucu kirası", html)

    def test_empty_book_shows_a_message_not_a_row_of_na(self):
        empty = Book.objects.create(name="Boş Defter")
        response = self.client.get(self.url(empty))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [])
        self.assertNotIn("N/A", response.content.decode())

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url(self.book))
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])
