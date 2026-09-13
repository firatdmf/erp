"""What the current-account rename left pointing at names that no longer exist.

9940e746 renamed Python identifiers. Anything that names one from outside
Python — a template variable, a data- attribute read back by JS, a code
format written into a management command — kept the old spelling, and
each of those failed quietly rather than loudly:

* the statement heading read a context variable the view stopped
  providing, and printed "Statement — " with no name;
* the equity expense page's currency hint read S.ccyCurrentAccount off a
  span that still carried the old attribute, so the hint was blank;
* move_current_accounts minted renumbered codes in a hardcoded prefix
  instead of the destination book's own.

Run with:
    python manage.py test accounting.test_current_account_rename_leftovers
"""
import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounting.management.commands.move_current_accounts import Command as MoveCommand
from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountSettings


class StatementHeading(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stmt", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.user.member.books.add(self.book)
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-007", name="TATYANA VARSOVA",
            type="customer", default_currency=self.usd,
        )

    def test_the_heading_names_the_account(self):
        r = self.client.get(reverse("accounts:statement", kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Statement — TATYANA VARSOVA")


class EquityExpenseStrings(SimpleTestCase):
    """The page's JS reads its translated strings off #expenseStrings via
    .dataset, so every S.someName it reads needs a data-some-name there."""

    def test_every_string_the_script_reads_is_on_the_span(self):
        path = Path(settings.BASE_DIR, "accounting/templates/accounting/add_equity_expense.html")
        src = path.read_text(encoding="utf-8")
        span = re.search(r'<span id="expenseStrings".*?></span>', src, re.S).group(0)
        provided = {
            re.sub(r"-(\w)", lambda m: m.group(1).upper(), name)
            for name in re.findall(r"\bdata-([\w-]+)=", span)
        }
        read = set(re.findall(r"\bS\.(\w+)", src))
        self.assertTrue(read)
        self.assertEqual(read - provided, set())


class MoveKeepsTheDestinationsCodeFormat(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.source = Book.objects.create(name="Laleli Fabric")
        self.target = Book.objects.create(name="Ergene Fabric")
        target_settings = CurrentAccountSettings.for_book(self.target)
        target_settings.current_account_code_prefix = "ERG"
        target_settings.current_account_code_padding = 4
        target_settings.save()

    def _account(self, book, code):
        return CurrentAccount.objects.create(
            book=book, code=code, name=code, type="customer",
            default_currency=self.usd, opening_balance=Decimal("0"),
        )

    def test_a_clashing_arrival_is_renumbered_in_the_targets_prefix(self):
        self._account(self.target, "ERG-0001")
        arriving = self._account(self.source, "ERG-0001")
        command = MoveCommand()
        new_code = command._allocate_codes(self.target.pk, [arriving], [arriving.pk])
        self.assertEqual(new_code, {arriving.pk: "ERG-0002"})
        self.assertEqual(command._next_seq(self.target.pk, [arriving], new_code), 3)
