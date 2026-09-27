# to run this test, use the command:
# python manage.py test accounting.tests.test_statement_readability

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement


class StatementReadabilityTests(TestCase):
    """The statement and the detail page have to say what they leave out.

    Twenty rows with no count read as the whole account; a Due Date
    column is dashes on every row but the few with terms; a note on the
    account belongs where the ledger is read; and a running balance is a
    line, not thirty-five numbers to subtract in your head.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stmt", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.user.member.books.add(self.book)
        self.account = CurrentAccount.objects.create(
            book=self.book, code="KARFF", name="DEMFIRAT KARVEN | ERGENE",
            type="intercompany", default_currency=self.usd,
        )

    def _row(self, amount, when, **extra):
        return CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, movement_type="adjustment",
            date=when, amount=Decimal(amount), currency=self.usd,
            amount_base=Decimal(amount), **extra,
        )

    def _statement(self, **params):
        return self.client.get(reverse("accounts:statement", kwargs={"pk": self.account.pk}), params)

    def _detail(self):
        return self.client.get(reverse("accounts:detail", kwargs={"pk": self.account.pk}))

    # ── detail page ────────────────────────────────────────────────
    def test_detail_says_how_many_rows_it_is_not_showing(self):
        for i in range(35):
            self._row("1.00", f"2026-07-{1 + i % 28:02d}")
        self.assertIn("Showing latest 20 of 35", self._detail().content.decode())

    def test_detail_keeps_quiet_when_everything_fits(self):
        for _ in range(5):
            self._row("1.00", "2026-07-01")
        html = self._detail().content.decode()
        self.assertNotIn("Showing latest", html)
        self.assertIn("Full Statement", html)

    # ── statement ──────────────────────────────────────────────────
    def test_there_is_no_due_date_column(self):
        self._row("100.00", "2026-07-16")
        self._row("-40.00", "2026-07-20", due_date="2026-08-15")
        html = self._statement().content.decode()
        # The heading, specifically: the phrase is in the page shell too.
        self.assertNotIn("<th>Due Date</th>", html)

    def test_a_due_date_reads_under_its_row_date(self):
        self._row("100.00", "2026-07-16")
        self._row("-40.00", "2026-07-20", due_date="2026-08-15")
        html = self._statement().content.decode()
        self.assertEqual(html.count('class="st-due"'), 1)
        self.assertIn("due 15.08.2026", html)

    def test_account_note_is_read_on_the_statement(self):
        self.account.notes = "Merged 15.09.2026: KARVEN HACİM MALLARI folded into this account."
        self.account.save()
        self.assertIn("KARVEN HACİM MALLARI folded into this account",
                      self._statement().content.decode())

    def test_running_balance_walks_the_rows_in_ledger_order(self):
        self._row("-297872.48", "2026-07-16", description="Hacim 1")
        self._row("872700.29", "2026-07-20", description="the opening")
        self._row("-500.00", "2026-07-27", description="x")
        # Read newest-first: the picture still goes oldest to newest.
        resp = self._statement(sort="desc")
        chart = resp.context["chart"]
        self.assertEqual([p["b"] for p in chart["points"]], [-297872.48, 574827.81, 574327.81])
        self.assertEqual(chart["points"][1]["s"], "the opening")
        self.assertIn('id="stmt-chart-data"', resp.content.decode())

    def test_a_single_row_is_a_number_not_a_line(self):
        self._row("100.00", "2026-07-16")
        resp = self._statement()
        self.assertIsNone(resp.context["chart"])
        self.assertNotIn('id="stmt-chart"', resp.content.decode())

    def test_series_starts_from_the_filtered_opening(self):
        self._row("100.00", "2026-07-16")
        self._row("50.00", "2026-08-01")
        self._row("-20.00", "2026-08-10")
        chart = self._statement(date_from="2026-08-01").context["chart"]
        self.assertEqual(chart["opening"], 100.0)
        self.assertEqual([p["b"] for p in chart["points"]], [150.0, 130.0])
