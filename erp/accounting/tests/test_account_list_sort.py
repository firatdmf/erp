"""The current-account list opens with whoever owes the most at the top.

Run with:
    python manage.py test accounting.tests.test_account_list_sort
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount


class TheListOpensOnTheBiggestDebt(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        user = get_user_model().objects.create_user(username="sorter", password="pw")
        user.member.books.set([self.book])
        self.client.force_login(user)
        # Names in the opposite order to the balances, so an A → Z list
        # cannot pass by accident.
        for code, name, balance in (("ACC-001", "AYDIN", "-300.00"),
                                    ("ACC-002", "BURSA", "0.00"),
                                    ("ACC-003", "ZEKİ", "1500.00"),
                                    ("ACC-004", "YILMAZ", "40.00")):
            CurrentAccount.objects.filter(pk=CurrentAccount.objects.create(
                book=self.book, code=code, name=name, default_currency=usd).pk
            ).update(cached_balance=Decimal(balance))

    def codes(self, **params):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.book.pk}),
                            params)
        self.assertEqual(r.status_code, 200)
        return [c.code for c in r.context["current_accounts"]], r.context["sort"]

    def test_by_default_the_most_owed_comes_first(self):
        # Owes us 1,500, owes us 40, settled, we owe 300.
        self.assertEqual(self.codes(),
                         (["ACC-003", "ACC-004", "ACC-002", "ACC-001"], "-balance"))

    def test_a_chosen_sort_still_wins(self):
        codes, sort = self.codes(sort="name")
        self.assertEqual(codes, ["ACC-001", "ACC-002", "ACC-004", "ACC-003"])
        self.assertEqual(sort, "name")
