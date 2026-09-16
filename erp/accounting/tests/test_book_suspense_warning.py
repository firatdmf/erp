"""The book page warns while anything sits in 1900 Suspense.

Run with:
    python manage.py test accounting.tests.test_book_suspense_warning
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_ledger import ensure_chart, suspense_report


class BookPageSuspenseWarning(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.a = CurrentAccount.objects.create(
            book=self.book, code="ACC-001", name="AHMET BALTAN", default_currency=self.usd)
        self.b = CurrentAccount.objects.create(
            book=self.book, code="ACC-002", name="COLİNS", default_currency=self.usd)
        user = get_user_model().objects.create_user("acct", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

    def _mv(self, account, kind, amount, **extra):
        return CurrentAccountMovement.objects.create(
            current_account=account, book=self.book, date="2026-09-15",
            amount=Decimal(amount), currency=self.usd, movement_type=kind,
            description=f"{kind} row", **extra)

    def _page(self):
        r = self.client.get(reverse("accounting:book_detail", kwargs={"pk": self.book.pk}))
        self.assertEqual(r.status_code, 200)
        return r

    def test_no_warning_when_suspense_is_empty(self):
        self._mv(self.a, "interest", "10.00")
        self.assertNotContains(self._page(), 'id="suspenseWarning"')

    def test_an_adjustment_raises_the_warning_and_is_listed(self):
        mv = self._mv(self.a, "adjustment", "-271.81")
        r = self._page()
        self.assertContains(r, 'id="suspenseWarning"')
        self.assertContains(r, "held in 1900 Suspense")
        self.assertContains(r, "AHMET BALTAN")
        self.assertContains(r, reverse("accounts:movement_edit",
                                       kwargs={"pk": self.a.pk, "mv_pk": mv.pk}))

    def test_reclassifying_clears_it(self):
        mv = self._mv(self.a, "adjustment", "-271.81")
        mv.movement_type = "write_off"
        mv.save()
        self.assertNotContains(self._page(), 'id="suspenseWarning"')

    def test_a_transfer_is_not_listed_as_a_decision(self):
        from django.contrib.contenttypes.models import ContentType

        from accounting.models_accounts import CurrentAccountTransfer
        ct = ContentType.objects.get_for_model(CurrentAccountTransfer)
        self._mv(self.a, "adjustment", "-50.00", source_type=ct, source_id=1)
        self._mv(self.b, "adjustment", "50.00", source_type=ct, source_id=1)
        report = suspense_report(self.book)
        self.assertEqual(report["balance"], Decimal("0.00"))
        self.assertEqual(report["items"], [])

    def test_the_balance_and_the_count_agree_with_the_ledger(self):
        self._mv(self.a, "adjustment", "-100.00")
        self._mv(self.b, "adjustment", "30.00")
        report = suspense_report(self.book)
        self.assertEqual(report["balance"], Decimal("70.00"))
        self.assertEqual(report["count"], 2)


class AnExpenseSomeonePaidIsAnExpense(TestCase):
    """An expense a customer settled on the book's behalf is filed as an
    adjustment on their account, but it is an expense, not a decision."""

    def test_it_posts_to_operating_expenses_not_suspense(self):
        from django.contrib.contenttypes.models import ContentType

        from accounting.models import EquityExpense, ExpenseCategory
        from accounting.services_ledger import balance_sheet

        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        ensure_chart()
        account = CurrentAccount.objects.create(
            book=book, code="ACC-001", name="DOĞAN TEKSTİL", default_currency=usd)
        expense = EquityExpense.objects.create(
            book=book, currency=usd, amount=Decimal("19942.00"), date="2026-09-15",
            description="Spent by Fırat", paid_by_current_account=account,
            category=ExpenseCategory.objects.create(name="Unrecorded"))
        CurrentAccountMovement.objects.create(
            current_account=account, book=book, date="2026-09-15",
            amount=Decimal("-19942.00"), currency=usd, movement_type="adjustment",
            source_type=ContentType.objects.get_for_model(EquityExpense),
            source_id=expense.pk)
        b = {r["code"]: r["balance"] for r in balance_sheet(book)["trial_balance"]["rows"]}
        self.assertEqual(b["5100"], Decimal("19942.00"))
        self.assertNotIn("1900", b)
        self.assertEqual(suspense_report(book)["balance"], Decimal("0.00"))
