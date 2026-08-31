"""An object page is refused when its row belongs to another book.

Collections were scoped by book; objects were not. The path deliberately
does not name the book — the row's FK does, and a path that could
disagree with the FK would be worse — but nothing then checked the row's
book either, so "the row knows its book" became "nobody checks it". A
member assigned only to Ergene could read a Laleli customer's statement,
open its invoices and payments, and edit its orders, by walking
sequential ids.

404 rather than 403, matching book_scoped: which books exist is not
something an unassigned member should learn from a status code.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, Payment
from accounting.models_accounts import CariAccount, Invoice


class ObjectPagesAreRefusedAcrossBooks(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        self.their_cari = self._cari(self.laleli, "Karven")
        self.my_cari = self._cari(self.ergene, "Bursa Tekstil")
        self.their_invoice = self._invoice(self.laleli, self.their_cari)
        self.their_payment = self._payment(self.laleli, self.their_cari)

        User = get_user_model()
        self.outsider = User.objects.create_user("ergene_only", password="pw")
        self.outsider.member.books.add(self.ergene)
        self.outsider.member.default_book = self.ergene
        self.outsider.member.save()
        self.boss = User.objects.create_superuser("boss", "b@t.com", "pw")

    def _cari(self, book, name):
        return CariAccount.objects.create(
            book=book, code=f"C-{book.pk}", name=name, type="customer",
            default_currency=self.usd)

    def _invoice(self, book, cari):
        return Invoice.objects.create(
            book=book, cari=cari, type="sales", status="draft",
            date="2026-08-21", due_date="2026-09-21",
            currency=self.usd, total=Decimal("100.00"))

    def _payment(self, book, cari):
        return Payment.objects.create(
            book=book, cari=cari, number="TAH-001", type="collection",
            method="cash", status="draft", date="2026-08-21",
            amount=Decimal("50.00"), currency=self.usd)

    def _urls(self):
        return {
            "cari detail": reverse("accounts:detail", args=[self.their_cari.pk]),
            "cari statement": reverse("accounts:statement", args=[self.their_cari.pk]),
            "cari edit": reverse("accounts:edit", args=[self.their_cari.pk]),
            "invoice": reverse("accounts:invoice_detail", args=[self.their_invoice.pk]),
            "payment": reverse("accounts:payment_detail", args=[self.their_payment.pk]),
        }

    def test_another_books_rows_are_all_refused(self):
        self.client.force_login(self.outsider)
        for label, url in self._urls().items():
            with self.subTest(page=label):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_it_is_404_not_403(self):
        """A 403 would confirm the row exists, which is the thing an
        unassigned member should not be able to establish."""
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(self._urls()["cari detail"]).status_code, 404)

    def test_their_own_book_is_untouched(self):
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse("accounts:detail",
                                    args=[self.my_cari.pk])).status_code, 200)

    def test_a_superuser_reaches_every_book(self):
        """member_books grants a superuser every book implicitly — an
        install's owner must not lock themselves out of a ledger."""
        self.client.force_login(self.boss)
        for label, url in self._urls().items():
            with self.subTest(page=label):
                self.assertEqual(self.client.get(url).status_code, 200)
