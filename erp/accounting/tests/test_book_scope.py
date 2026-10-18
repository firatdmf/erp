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

from django.utils import timezone

from accounting.models import Book, CheckOrPromissoryNote, CurrencyCategory, Payment
from accounting.models_accounts import CurrentAccount


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

        CurrentAccount.objects.create(book=self.ergene, code="ACC-001", name="Gürhan",
                                   default_currency=self.usd,
                                   cached_balance=Decimal("100.00"))
        CurrentAccount.objects.create(book=self.laleli, code="00010", name="Ercan",
                                   default_currency=self.usd,
                                   cached_balance=Decimal("900.00"))

    def test_the_list_shows_only_its_own_book(self):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.ergene.pk}))
        self.assertEqual(r.status_code, 200)
        codes = {c.code for c in r.context["current_accounts"]}
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
        for name in ("report_trial_balance", "report_credit_limit"):
            with self.subTest(report=name):
                ok = self.client.get(reverse(f"accounts:{name}",
                                             kwargs={"book_id": self.ergene.pk}))
                self.assertEqual(ok.status_code, 200)
                denied = self.client.get(reverse(f"accounts:{name}",
                                                 kwargs={"book_id": self.laleli.pk}))
                self.assertEqual(denied.status_code, 404)

    def test_the_payment_list_shows_only_its_own_book(self):
        """It listed every book's payments under whichever book was open,
        and added them into that book's collected total."""
        for book, code, number, amount in (
            (self.ergene, "ACC-001", "COL-2026-000001", "100.00"),
            (self.laleli, "00010", "COL-2026-000002", "900.00"),
        ):
            Payment.objects.create(
                current_account=CurrentAccount.objects.get(code=code), book=book,
                number=number, type="collection", method="other",
                status="draft", date="2026-08-17", amount=Decimal(amount),
                currency=self.usd,
            ).confirm()
        r = self.client.get(reverse("accounts:payment_list",
                                    kwargs={"book_id": self.ergene.pk}))
        self.assertEqual([p.number for p in r.context["payments"]],
                         ["COL-2026-000001"])
        self.assertEqual(r.context["n"], 1)
        self.assertEqual(r.context["collection_sum"], Decimal("100.00"))

    def test_the_check_list_shows_only_its_own_book(self):
        today = timezone.localdate()
        for book, code, serial in ((self.ergene, "ACC-001", "CHK-ERG"),
                                   (self.laleli, "00010", "CHK-LAL")):
            CheckOrPromissoryNote.objects.create(
                book=book, current_account=CurrentAccount.objects.get(code=code),
                instrument="check", direction="received", serial_no=serial,
                amount=Decimal("500.00"), currency=self.usd,
                issue_date=today, due_date=today,
            )
        r = self.client.get(reverse("accounts:check_list",
                                    kwargs={"book_id": self.ergene.pk}))
        self.assertEqual([c.serial_no for c in r.context["checks"]], ["CHK-ERG"])

    def test_the_payment_form_offers_only_its_own_book(self):
        """The dropdown listed every book's customers by name."""
        from accounting.models import CashAccount
        CashAccount.objects.create(book=self.ergene, name="Ergene Till", currency=self.usd)
        CashAccount.objects.create(book=self.laleli, name="Laleli Till", currency=self.usd)
        r = self.client.get(reverse("accounts:payment_create",
                                    kwargs={"book_id": self.ergene.pk}))
        self.assertEqual({c.code for c in r.context["current_account_options"]},
                         {"ACC-001"})
        self.assertEqual({c.name for c in r.context["cash_accounts"]}, {"Ergene Till"})
        self.assertNotContains(r, "Ercan")

    def test_the_payment_form_will_not_open_on_another_books_account(self):
        other = CurrentAccount.objects.get(code="00010")
        r = self.client.get(reverse("accounts:payment_create",
                                    kwargs={"book_id": self.ergene.pk}),
                            {"account": other.pk})
        self.assertIsNone(r.context["prefilled_current_account"])
        self.assertNotContains(r, "Ercan")

    def test_a_payment_cannot_be_posted_to_another_books_account(self):
        other = CurrentAccount.objects.get(code="00010")
        r = self.client.post(
            reverse("accounts:payment_create", kwargs={"book_id": self.ergene.pk}),
            {"account": other.pk, "amount": "50.00", "type": "collection",
             "method": "other", "currency": self.usd.pk, "date": "2026-08-17"},
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Payment.objects.exists())

    def test_a_payment_cannot_draw_on_another_books_cash_account(self):
        from accounting.models import CashAccount
        till = CashAccount.objects.create(book=self.laleli, name="Laleli Till",
                                          currency=self.usd)
        mine = CurrentAccount.objects.get(code="ACC-001")
        r = self.client.post(
            reverse("accounts:payment_create", kwargs={"book_id": self.ergene.pk}),
            {"account": mine.pk, "amount": "50.00", "type": "collection",
             "method": "cash", "currency": self.usd.pk, "date": "2026-08-17",
             "cash_account": till.pk},
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Payment.objects.exists())

    def test_the_check_form_offers_only_its_own_book(self):
        r = self.client.get(reverse("accounts:check_create",
                                    kwargs={"book_id": self.ergene.pk}))
        self.assertEqual({c.code for c in r.context["current_account_options"]},
                         {"ACC-001"})
        self.assertNotContains(r, "Ercan")

    def test_a_check_cannot_be_written_on_another_books_account(self):
        other = CurrentAccount.objects.get(code="00010")
        r = self.client.post(
            reverse("accounts:check_create", kwargs={"book_id": self.ergene.pk}),
            {"account": other.pk, "amount": "50.00", "serial_no": "CHK-X",
             "currency": self.usd.pk},
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(CheckOrPromissoryNote.objects.exists())

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
        current_account = CurrentAccount.objects.get(name="Yeni Tekstil")
        self.assertEqual(current_account.book_id, self.laleli.pk)

    def test_a_new_account_starts_in_the_books_currency(self):
        """Not in whichever currency sorts first — EUR came before TRY."""
        CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.ergene.base_currency = try_
        self.ergene.save(update_fields=["base_currency"])
        r = self.client.get(reverse("accounts:create", kwargs={"book_id": self.ergene.pk}))
        self.assertContains(r, f'<option value="{try_.pk}" selected>', html=False)


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
