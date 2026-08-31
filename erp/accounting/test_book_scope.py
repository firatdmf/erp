"""The ledger shows one book, and only a book you are assigned.

Two things are being pinned here. That a page's totals cover exactly one
business — /accounting/accounts/ used to list every book at once and add
their balances together, so a factory's receivables were summed with a
wholesaler's. And that the book in the path is a permission boundary, not
a display preference: typing another book's id must not open it.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount


class BookScopedLedger(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.laleli = Book.objects.create(name="Laleli Fabric")

        self.user = get_user_model().objects.create_user(username="ergene_only", password="pw")
        self.member = self.user.member
        self.member.books.set([self.ergene])
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

        CariAccount.objects.create(book=self.ergene, code="ACC-001", name="Gürhan",
                                   default_currency=self.usd,
                                   cached_balance=Decimal("100.00"))
        CariAccount.objects.create(book=self.laleli, code="00010", name="Ercan",
                                   default_currency=self.usd,
                                   cached_balance=Decimal("900.00"))

    def test_the_list_shows_only_its_own_book(self):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.ergene.pk}))
        self.assertEqual(r.status_code, 200)
        codes = {c.code for c in r.context["caris"]}
        self.assertEqual(codes, {"ACC-001"})

    def test_the_totals_cover_one_business(self):
        """The bug this replaced: 100 + 900 presented as one number."""
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.ergene.pk}))
        self.assertEqual(r.context["owes_us"], Decimal("100.00"))
        self.assertEqual(r.context["total_count"], 1)

    def test_a_book_you_are_not_assigned_is_not_there(self):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.laleli.pk}))
        self.assertEqual(r.status_code, 404)

    def test_a_book_that_does_not_exist_is_not_there(self):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": 99999}))
        self.assertEqual(r.status_code, 404)

    def test_a_superuser_reaches_every_book(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.laleli.pk}))
        self.assertEqual(r.status_code, 200)

    def test_the_switcher_offers_only_assigned_books(self):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.ergene.pk}))
        self.assertEqual([b.pk for b in r.context["books"]], [self.ergene.pk])

    def test_reports_are_scoped_too(self):
        for name in ("report_aging", "report_trial_balance",
                     "report_credit_limit", "report_due_calendar"):
            with self.subTest(report=name):
                ok = self.client.get(reverse(f"accounts:{name}",
                                             kwargs={"book_id": self.ergene.pk}))
                self.assertEqual(ok.status_code, 200)
                denied = self.client.get(reverse(f"accounts:{name}",
                                                 kwargs={"book_id": self.laleli.pk}))
                self.assertEqual(denied.status_code, 404)

    def test_a_new_account_lands_in_the_book_named_in_the_path(self):
        """Not in the member's working book — the page said which."""
        self.member.default_book = None
        self.member.books.add(self.laleli)
        self.member.save(update_fields=["default_book"])
        r = self.client.post(
            reverse("accounts:create", kwargs={"book_id": self.laleli.pk}),
            {"entity_type": "company", "name": "Yeni Tekstil",
             "type": "customer", "default_currency": self.usd.pk},
        )
        self.assertIn(r.status_code, (200, 302))
        cari = CariAccount.objects.get(name="Yeni Tekstil")
        self.assertEqual(cari.book_id, self.laleli.pk)


class LegacyLedgerUrls(TestCase):
    """The pre-split addresses are in bookmarks; they must still land."""

    def setUp(self):
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.user = get_user_model().objects.create_user(username="bookmarker", password="pw")
        self.member = self.user.member
        self.member.books.set([self.ergene])
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

    def test_the_old_list_url_redirects_to_the_working_book(self):
        r = self.client.get(reverse("accounts:legacy_list"))
        self.assertRedirects(
            r, reverse("accounts:list", kwargs={"book_id": self.ergene.pk}),
            fetch_redirect_response=False)

    def test_the_query_string_survives_the_redirect(self):
        r = self.client.get(reverse("accounts:legacy_list"), {"q": "gürhan"})
        self.assertIn("q=g", r["Location"])
