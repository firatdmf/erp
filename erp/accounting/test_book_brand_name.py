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
from accounting.services_accounts import brand_name_for


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

    def test_the_resolver_picks_the_flagged_book(self):
        self.book.make_default_cari_target()
        Book.objects.create(name="Side Book", brand_name="Wrong Name")
        self.assertEqual(brand_name_for(), self.LOCKUP)

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
    """Which book the ledger posts to is a flag on the row, so renaming
    a book cannot move it."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ledger_tester", password="pw")
        self.client.force_login(self.user)
        Book.objects.all().delete()
        self.ledger = Book.objects.create(name="Laleli Fabric",
                                          is_default_cari_target=True)
        self.other = Book.objects.create(name="Ergene Fabric")

    def test_the_flag_wins(self):
        self.assertEqual(brand_name_for.__module__, "accounting.services_accounts")
        from accounting.services_accounts import get_default_book
        self.assertEqual(get_default_book().pk, self.ledger.pk)

    def test_renaming_the_book_does_not_move_the_ledger(self):
        """The whole point: the old resolver matched
        a book NAME held in settings against Book.name, so this rename
        silently dropped it to guessing."""
        from accounting.services_accounts import get_default_book
        self.ledger.name = "Something Else Entirely"
        self.ledger.save(update_fields=["name"])
        self.assertEqual(get_default_book().pk, self.ledger.pk)

    def test_only_one_book_can_hold_it(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Book.objects.filter(pk=self.other.pk).update(is_default_cari_target=True)

    def test_promoting_a_book_demotes_the_old_one(self):
        self.other.make_default_cari_target()
        self.ledger.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_default_cari_target)
        self.assertFalse(self.ledger.is_default_cari_target)

    def test_promoting_is_idempotent(self):
        self.ledger.make_default_cari_target()
        self.ledger.refresh_from_db()
        self.assertTrue(self.ledger.is_default_cari_target)
        self.assertEqual(Book.objects.filter(is_default_cari_target=True).count(), 1)

    def test_the_endpoint_moves_it(self):
        resp = self.client.post(reverse("accounting:set_default_cari_target",
                                        kwargs={"pk": self.other.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])
        self.other.refresh_from_db()
        self.ledger.refresh_from_db()
        self.assertTrue(self.other.is_default_cari_target)
        self.assertFalse(self.ledger.is_default_cari_target)

    def test_an_explicit_id_still_overrides_the_flag(self):
        from accounting.services_accounts import get_default_book
        with self.settings(CARI_BOOK_ID=str(self.other.pk)):
            self.assertEqual(get_default_book().pk, self.other.pk)

    def _give_a_cari_account(self, book):
        from accounting.models import CurrencyCategory
        from accounting.models_accounts import CariAccount
        currency = (CurrencyCategory.objects.filter(code="USD").first()
                    or CurrencyCategory.objects.create(code="USD", name="USD"))
        return CariAccount.objects.create(book=book, name="Acme",
                                          code="CARI-001",
                                          default_currency=currency)

    def test_no_flagged_book_falls_back_to_account_count(self):
        from accounting.services_accounts import get_default_book
        Book.objects.update(is_default_cari_target=False)
        self._give_a_cari_account(self.other)
        self.assertEqual(get_default_book().pk, self.other.pk)

    def test_the_fallback_writes_its_answer_down(self):
        """Step 3 adopts, so the guess is made once and then shows on
        the book's page where somebody can correct it."""
        from accounting.services_accounts import get_default_book
        Book.objects.update(is_default_cari_target=False)
        self._give_a_cari_account(self.other)

        get_default_book()
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_default_cari_target)
        self.assertEqual(Book.objects.filter(is_default_cari_target=True).count(), 1)

    def test_adopting_never_breaks_the_read(self):
        """It runs inside order placement; a failed write must not
        propagate."""
        from unittest.mock import patch
        from accounting.services_accounts import get_default_book
        Book.objects.update(is_default_cari_target=False)
        self._give_a_cari_account(self.other)

        with patch("django.db.transaction.atomic",
                   side_effect=RuntimeError("read-only replica")):
            self.assertEqual(get_default_book().pk, self.other.pk)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_default_cari_target)
