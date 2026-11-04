"""An expense the cash account cannot cover is refused whole.

The form used to save the expense, try to post it, and on "balance cannot
be less than zero" show the error while keeping the saved row. The row
stood in the expense list with no cash entry behind it, and deleting it
later handed the drawer back money that had never left — Laleli's Drawer
(TRY) came to read 800 more than its own entries that way (LL24).
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CashAccount, CashTransactionEntry, CurrencyCategory,
    EquityExpense, ExpenseCategory,
)
from accounting.views import post_expense


class RefusedExpenseTests(TestCase):

    def setUp(self):
        user = get_user_model().objects.create_superuser(username="till", password="pw")
        self.client.force_login(user)
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.try_)
        self.drawer = CashAccount.objects.create(
            book=self.book, name="Drawer", currency=self.try_, balance=Decimal("720.00"),
        )
        self.meals = ExpenseCategory.objects.create(name="Meals")
        self.ct = ContentType.objects.get_for_model(EquityExpense)

    def payload(self, **overrides):
        data = {
            "book": self.book.pk, "category": self.meals.pk,
            "cash_account": self.drawer.pk, "paid_by_current_account": "",
            "currency": self.try_.pk, "amount": "800.00",
            "date": "2026-11-03", "exchange_rate": "", "description": "",
        }
        data.update(overrides)
        return data

    def balance(self):
        self.drawer.refresh_from_db()
        return self.drawer.balance

    def expense(self, amount):
        expense = EquityExpense.objects.create(
            book=self.book, category=self.meals, cash_account=self.drawer,
            currency=self.try_, amount=Decimal(amount), date="2026-11-03",
        )
        post_expense(self.book, expense)
        return expense

    def test_a_refused_expense_is_not_saved(self):
        response = self.client.post(
            reverse("accounting:add_equity_expense", kwargs={"pk": self.book.pk}),
            self.payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not hold enough")
        self.assertFalse(EquityExpense.objects.exists())
        self.assertEqual(self.balance(), Decimal("720.00"))

    def test_a_refused_edit_leaves_the_expense_as_it_was(self):
        expense = self.expense("100.00")
        response = self.client.post(
            reverse("accounting:edit_equity_expense",
                    kwargs={"pk": self.book.pk, "expense_pk": expense.pk}),
            self.payload(amount="5000.00"),
        )
        self.assertContains(response, "does not hold enough")
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal("100.00"))
        self.assertEqual(self.balance(), Decimal("620.00"))
        self.assertEqual(
            CashTransactionEntry.objects.filter(content_type=self.ct, content_pk=expense.pk).count(), 1
        )

    def test_deleting_an_expense_gives_back_only_what_its_rows_took(self):
        # An expense with no cash row: left by the old form, or by anything
        # else whose posting never landed. It took nothing, so it gives
        # nothing back.
        orphan = EquityExpense.objects.create(
            book=self.book, category=self.meals, cash_account=self.drawer,
            currency=self.try_, amount=Decimal("990.00"), date="2026-11-03",
        )
        self.client.post(reverse(
            "accounting:delete_equity_expense",
            kwargs={"pk": self.book.pk, "expense_pk": orphan.pk},
        ))
        self.assertFalse(EquityExpense.objects.filter(pk=orphan.pk).exists())
        self.assertEqual(self.balance(), Decimal("720.00"))

    def test_deleting_a_posted_expense_still_gives_the_cash_back(self):
        expense = self.expense("200.00")
        self.assertEqual(self.balance(), Decimal("520.00"))
        self.client.post(reverse(
            "accounting:delete_equity_expense",
            kwargs={"pk": self.book.pk, "expense_pk": expense.pk},
        ))
        self.assertEqual(self.balance(), Decimal("720.00"))

    def test_match_balances_sets_the_balance_to_its_entries(self):
        # 720 held with no entries at all: the entries say 0.
        call_command("repair_cash_running_balance", "--book", str(self.book.pk),
                     "--apply", "--match-balances", stdout=open("/dev/null", "w"))
        self.assertEqual(self.balance(), Decimal("0.00"))
