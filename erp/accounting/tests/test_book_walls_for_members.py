"""A member of one book reads that book's accounts and no other's.

These were pages under /accounting/books/<id>/ that still read across
every book: the all-accounts statement listed every business's customers
and balances, the reports offered every book by name, and the reports
landing page counted every book's accounts over their limit.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission


class BookWallsForMembers(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.almaty = Book.objects.create(name="Almaty Branch")
        cls.laleli = Book.objects.create(name="Laleli Shopfront")
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")

        def account(book, code, name):
            acc = CurrentAccount.objects.create(
                book=book, code=code, name=name, type="customer", default_currency=usd)
            # Set straight on the row: the balance is what the pages read,
            # and no movement is needed to say what it is.
            CurrentAccount.objects.filter(pk=acc.pk).update(
                cached_balance=Decimal("500.00"), credit_limit=Decimal("100.00"))
            return acc

        cls.own = account(cls.almaty, "ALM-1", "Steppe Curtains")
        cls.other = account(cls.laleli, "LAL-1", "Bosphorus Drapes")

        cls.user = User.objects.create_user("burak_walls", password="pw")
        member = cls.user.member
        member.books.set([cls.almaty])
        member.default_book = cls.almaty
        member.save(update_fields=["default_book"])
        member.permissions.add(Permission.objects.get_or_create(name="middle_manager")[0])

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def page(self, route):
        response = self.client.get(f"/accounting/books/{self.almaty.pk}/{route}")
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_statement_lists_only_this_book(self):
        response = self.page("accounts/statement/")
        self.assertContains(response, "Steppe Curtains")
        self.assertNotContains(response, "Bosphorus Drapes")

    def test_the_reports_name_no_other_book(self):
        for route in ("reports/trial-balance/", "reports/credit-limit/"):
            with self.subTest(route=route):
                self.assertNotContains(self.page(route), "Laleli Shopfront")

    def test_the_credit_limit_report_lists_only_this_book(self):
        response = self.page("reports/credit-limit/?view=all")
        self.assertContains(response, "Steppe Curtains")
        self.assertNotContains(response, "Bosphorus Drapes")

    def test_the_reports_page_counts_only_this_book(self):
        self.assertEqual(self.page("reports/").context["over_limit_count"], 1)

    def test_another_books_statement_is_not_found(self):
        response = self.client.get(f"/accounting/books/{self.laleli.pk}/accounts/statement/")
        self.assertEqual(response.status_code, 404)
