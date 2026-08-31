# to run this test, use the command:
# python manage.py test accounting.test_book_brand_name

import io
import json
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from accounting.services_accounts import brand_name_for, get_default_book


class BookBrandNameField(TestCase):
    """The name a book's documents sign with, held on the book itself."""

    LOCKUP = "DEMFIRAT® | Karven Home Collection"

    def setUp(self):
        self.book = Book.objects.create(name="DEMFIRAT", brand_name=self.LOCKUP)

    def test_the_books_own_name_wins(self):
        self.assertEqual(self.book.effective_brand_name, self.LOCKUP)

    def test_blank_falls_back_to_the_brand_profile(self):
        self.book.brand_name = ""
        self.assertEqual(self.book.effective_brand_name,
                         settings.BRAND_DISPLAY_NAME)

    def test_it_is_separate_from_the_ledger_name(self):
        """`name` is the short internal handle and stays unique; the
        printed name is longer and need not be."""
        other = Book.objects.create(name="KARVEN", brand_name=self.LOCKUP)
        self.assertEqual(other.effective_brand_name,
                         self.book.effective_brand_name)
        self.assertNotEqual(other.name, self.book.name)

    def test_the_resolver_picks_the_acting_members_book(self):
        """A document signs with the name of the business that issued
        it, and which business that is follows the person issuing it."""
        Book.objects.create(name="Side Book", brand_name="Wrong Name")
        user = get_user_model().objects.create_user(
            username="brand_tester", password="pw")
        member = user.member
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.assertEqual(brand_name_for(get_default_book(member)), self.LOCKUP)

    def test_the_resolver_survives_a_database_with_no_books(self):
        Book.objects.all().delete()
        self.assertTrue(brand_name_for())


class SeedMigration(TestCase):
    """0073 backfills the books that predate the field."""

    def test_existing_books_were_given_the_brand_name(self):
        # The migration ran when this test database was built; any book
        # created since starts blank, so assert on the migration's rule
        # rather than on rows it can no longer see.
        book = Book.objects.create(name="Fresh Book")
        self.assertEqual(book.brand_name, "")
        self.assertEqual(book.effective_brand_name, settings.BRAND_DISPLAY_NAME)


class BrandNameEditor(TestCase):
    """Inline editor on the book detail page header."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="brand_tester", password="pw")
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Demfirat", brand_name="Old Name")

    def url(self):
        return reverse("accounting:set_book_brand_name",
                       kwargs={"pk": self.book.pk})

    def test_it_saves_and_returns_the_effective_name(self):
        resp = self.client.post(self.url(), {"brand_name": "New Name"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content),
                         {"success": True, "brand_name": "New Name",
                          "effective": "New Name"})
        self.book.refresh_from_db()
        self.assertEqual(self.book.brand_name, "New Name")

    def test_blank_is_valid_and_reports_the_default(self):
        """Unlike `name`, empty is a real choice here — it means "use
        the brand default" — so the response says what that resolves to."""
        resp = self.client.post(self.url(), {"brand_name": ""})
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body["brand_name"], "")
        self.assertEqual(body["effective"], settings.BRAND_DISPLAY_NAME)

    def test_it_leaves_the_ledger_name_alone(self):
        self.client.post(self.url(), {"brand_name": "X", "name": "Hijacked"})
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat")


class InvoiceIssuer(TestCase):
    """An invoice signs with its own book."""

    def setUp(self):
        from accounting.models import CurrencyCategory
        from accounting.models_accounts import CariAccount, Invoice
        self.book = Book.objects.create(name="DEMFIRAT",
                                        brand_name="Karven Home Collection")
        currency = (CurrencyCategory.objects.filter(code="USD").first()
                    or CurrencyCategory.objects.create(code="USD", name="USD"))
        cari = CariAccount.objects.create(book=self.book, name="Acme",
                                          code="CARI-001",
                                          default_currency=currency)
        self.invoice = Invoice.objects.create(
            book=self.book, cari=cari, currency=currency, number="1",
            date=date(2026, 8, 20), due_date=date(2026, 9, 20),
            total=Decimal("100.00"))

    def test_it_takes_the_name_from_its_book(self):
        self.assertEqual(self.invoice.issuer_display_name,
                         "Karven Home Collection")

    def test_a_per_invoice_issuer_still_wins(self):
        self.invoice.issuer_name = "Demfirat Export A.Ş."
        self.assertEqual(self.invoice.issuer_display_name,
                         "Demfirat Export A.Ş.")

    def test_the_legal_suffix_is_not_pinned_onto_an_entered_name(self):
        """BRAND_LEGAL_SUFFIX pads the settings fallback only — appending
        it to a lockup would print "… Karven Home Collection SAN. TİC.
        LTD. ŞTİ." on a tax document."""
        self.assertNotIn(settings.BRAND_LEGAL_SUFFIX,
                         self.invoice.issuer_display_name)

    def test_the_settings_fallback_still_carries_the_legal_suffix(self):
        self.book.brand_name = ""
        self.book.save(update_fields=["brand_name"])
        self.invoice.refresh_from_db()
        self.assertEqual(
            self.invoice.issuer_display_name,
            f"{settings.BRAND_NAME} {settings.BRAND_LEGAL_SUFFIX}".strip())

    def test_the_excel_and_the_printed_invoice_agree(self):
        import openpyxl
        from accounting.invoice_excel import build_invoice_workbook
        wb = build_invoice_workbook(self.invoice)
        text = " ".join(
            str(c.value) for row in wb.active.iter_rows() for c in row
            if c.value is not None)
        self.assertIn(self.invoice.issuer_display_name, text)


class CariLedgerBook(TestCase):
    """Which book work lands in is a fact about the member doing it."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ledger_tester", password="pw")
        self.client.force_login(self.user)
        Book.objects.all().delete()
        self.ledger = Book.objects.create(name="Laleli Fabric")
        self.other = Book.objects.create(name="Ergene Fabric")
        self.member = self.user.member
        self.member.books.set([self.ledger])
        self.member.default_book = self.ledger
        self.member.save(update_fields=["default_book"])

    def test_the_working_book_wins(self):
        self.assertEqual(brand_name_for.__module__, "accounting.services_accounts")
        from accounting.services_accounts import get_default_book
        self.assertEqual(get_default_book(self.member).pk, self.ledger.pk)

    def test_renaming_the_book_does_not_move_the_ledger(self):
        """The original resolver matched a book NAME held in settings
        against Book.name, so a rename silently dropped it to guessing."""
        from accounting.services_accounts import get_default_book
        self.ledger.name = "Something Else Entirely"
        self.ledger.save(update_fields=["name"])
        self.assertEqual(get_default_book(self.member).pk, self.ledger.pk)

    def test_a_book_they_lost_access_to_is_not_used(self):
        """Unassigning a book has to move their work off it too —
        otherwise the stale FK keeps posting into a book they can no
        longer open."""
        from accounting.services_accounts import get_default_book
        self.member.books.set([self.other])
        self.assertEqual(get_default_book(self.member).pk, self.other.pk)

    def test_a_member_who_never_picked_gets_their_assigned_book(self):
        from accounting.services_accounts import get_default_book
        self.member.default_book = None
        self.member.save(update_fields=["default_book"])
        self.member.books.set([self.other])
        self.assertEqual(get_default_book(self.member).pk, self.other.pk)

    def test_a_superuser_may_use_any_book(self):
        from accounting.services_accounts import member_books
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        self.member.books.clear()
        self.assertEqual(member_books(self.member).count(), 2)

    def test_an_unassigned_book_is_refused(self):
        from accounting.services_accounts import member_can_use_book
        self.assertFalse(member_can_use_book(self.member, self.other))
        self.assertTrue(member_can_use_book(self.member, self.ledger))

    def test_the_endpoint_refuses_an_unassigned_book(self):
        resp = self.client.post(reverse("accounting:set_my_working_book",
                                        kwargs={"pk": self.other.pk}))
        self.assertEqual(resp.status_code, 403)
        self.member.refresh_from_db()
        self.assertEqual(self.member.default_book_id, self.ledger.pk)

    def test_the_endpoint_moves_the_working_book(self):
        self.member.books.add(self.other)
        resp = self.client.post(reverse("accounting:set_my_working_book",
                                        kwargs={"pk": self.other.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])
        self.member.refresh_from_db()
        self.assertEqual(self.member.default_book_id, self.other.pk)

    def test_memberless_work_uses_the_pinned_id(self):
        """Cron, imports and the shell have nobody at the keyboard, so
        CARI_BOOK_ID is the only place left to say which business they
        belong to."""
        from accounting.services_accounts import get_default_book
        with self.settings(CARI_BOOK_ID=str(self.other.pk)):
            self.assertEqual(get_default_book(None).pk, self.other.pk)
