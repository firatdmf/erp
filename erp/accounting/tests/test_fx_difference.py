# to run this test, use the command:
# python manage.py test accounting.tests.test_fx_difference

"""What the rate did, stated plainly and recorded only when asked.

A euro customer owes euros. The book carries that in dollars at the rate of
each movement's own day, so once the rate moves the carrying value stops
matching what the balance is worth. That gap is an FX gain or loss; it is
shown with the rates behind it, and posted to 5900 only when someone
decides to — never behind anyone's back, and never by changing what the
customer owes.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_fx import (
    book_fx_positions, fx_position, is_foreign, post_fx_difference,
)


class FxDifferenceTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.euroland = CurrentAccount.objects.create(
            book=self.book, code="ACC-EUR", name="Euroland", type="customer",
            default_currency=self.eur)
        self.dollarland = CurrentAccount.objects.create(
            book=self.book, code="ACC-USD", name="Dollarland", type="customer",
            default_currency=self.usd)

    def _sale(self, account, amount, currency, rate):
        with patch("accounting.services.get_exchange_rate", return_value=rate):
            return CurrentAccountMovement.objects.create(
                current_account=account, book=self.book, date="2026-09-01",
                amount=Decimal(amount), currency=currency,
                movement_type="invoice_sale", description="Sale")

    # ── Which accounts can even have one ────────────────────────────
    def test_only_a_foreign_account_has_a_position(self):
        self.assertTrue(is_foreign(self.euroland))
        self.assertFalse(is_foreign(self.dollarland))
        self.assertIsNone(fx_position(self.dollarland))

    # ── What it says ────────────────────────────────────────────────
    def test_it_states_the_gap_with_the_rates_behind_it(self):
        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))   # booked $1,100
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            pos = fx_position(self.euroland)
        self.assertEqual(pos["own_balance"], Decimal("1000.00"))   # owed: €1,000
        self.assertEqual(pos["base_balance"], Decimal("1100.00"))  # carried: $1,100
        self.assertEqual(pos["rate"], Decimal("1.20"))
        self.assertEqual(pos["base_at_rate"], Decimal("1200.00"))  # worth: $1,200
        self.assertEqual(pos["difference"], Decimal("100.00"))     # gain: $100
        self.assertEqual([r["rate"] for r in pos["rows"]], [Decimal("1.10000000")])

    def test_a_falling_rate_is_a_loss(self):
        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.00")):
            self.assertEqual(fx_position(self.euroland)["difference"], Decimal("-100.00"))

    # ── What posting it does, and does not, change ──────────────────
    def test_posting_moves_the_books_value_and_not_what_is_owed(self):
        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            mv = post_fx_difference(self.euroland)
        self.assertIsNotNone(mv)
        self.assertEqual(mv.movement_type, "fx_adjustment")
        self.assertEqual(mv.currency, self.usd)
        self.assertEqual(mv.amount, Decimal("100.00"))

        self.euroland.refresh_from_db()
        # The customer still owes exactly €1,000 …
        self.assertEqual(self.euroland.own_currency_balance(), Decimal("1000.00"))
        # … and the book now carries it at what it is worth.
        self.assertEqual(self.euroland.cached_balance, Decimal("1200.00"))

    def test_posting_twice_records_nothing_the_second_time(self):
        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            self.assertIsNotNone(post_fx_difference(self.euroland))
            self.assertEqual(fx_position(self.euroland)["difference"], Decimal("0.00"))
            self.assertIsNone(post_fx_difference(self.euroland))
        self.assertEqual(
            CurrentAccountMovement.objects.filter(movement_type="fx_adjustment").count(), 1)

    def test_it_reaches_the_foreign_exchange_line(self):
        from accounting.services_posting import lines_for_movement

        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            mv = post_fx_difference(self.euroland)
        codes = {line["code"] for line in lines_for_movement(mv)}
        self.assertIn("5900", codes)   # Foreign Exchange Gain/Loss
        self.assertIn("1200", codes)   # Accounts Receivable

    # ── The book's view ─────────────────────────────────────────────
    def test_the_book_report_totals_gains_against_losses(self):
        other = CurrentAccount.objects.create(
            book=self.book, code="ACC-EUR2", name="Eurotwo", type="customer",
            default_currency=self.eur)
        self._sale(self.euroland, "1000.00", self.eur, Decimal("1.10"))   # + at 1.20
        self._sale(other, "500.00", self.eur, Decimal("1.30"))            # − at 1.20
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            report = book_fx_positions(self.book)
        self.assertEqual(report["total"], Decimal("50.00"))   # +100 and −50
        self.assertEqual([r["account"].code for r in report["rows"]],
                         ["ACC-EUR", "ACC-EUR2"])
        # A dollar account is not in it at all: the rate cannot touch it.
        self.assertNotIn("ACC-USD", [r["account"].code for r in report["rows"]])


class FxScreensTest(TestCase):
    """The two places the difference is meant to be visible."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-EUR", name="Euroland", type="customer",
            default_currency=self.eur)
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.10")):
            CurrentAccountMovement.objects.create(
                current_account=self.account, book=self.book, date="2026-09-01",
                amount=Decimal("1000.00"), currency=self.eur,
                movement_type="invoice_sale", description="Sale")

        user = get_user_model().objects.create_superuser("firat_fx", "a@b.c", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def test_the_account_page_shows_the_difference(self):
        from django.urls import reverse

        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            r = self.client.get(reverse("accounts:detail", args=[self.account.pk]))
        self.assertEqual(r.status_code, 200)
        fx = r.context["fx"]
        self.assertEqual(fx["difference"], Decimal("100.00"))
        self.assertContains(r, "Exchange gain")
        self.assertContains(r, "Record the difference")

    def test_the_report_explains_what_happens_if_nobody_records_it(self):
        from django.urls import reverse

        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            r = self.client.get(reverse("accounts:fx_report", kwargs={"book_id": self.book.pk}))
        self.assertContains(r, "What happens if a difference is never recorded")
        self.assertContains(r, "We Owe")           # the residual, named
        self.assertContains(r, "5900")             # where the loss belongs
        self.assertContains(r, "Month end is swept automatically")

    def test_the_book_report_lists_it(self):
        from django.urls import reverse

        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            r = self.client.get(reverse("accounts:fx_report", kwargs={"book_id": self.book.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["report"]["total"], Decimal("100.00"))
        self.assertContains(r, "Euroland")

    def test_the_button_records_it_and_says_what_it_did(self):
        from django.urls import reverse

        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            r = self.client.post(reverse("accounts:fx_post", args=[self.account.pk]),
                                 follow=True)
        self.assertEqual(r.status_code, 200)
        messages = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("Exchange rate difference recorded" in m for m in messages), messages)
        self.assertTrue(any("still owes" in m for m in messages), messages)

        self.account.refresh_from_db()
        self.assertEqual(self.account.own_currency_balance(), Decimal("1000.00"))
        self.assertEqual(self.account.cached_balance, Decimal("1200.00"))

    def test_pressing_it_twice_records_once(self):
        from django.urls import reverse

        url = reverse("accounts:fx_post", args=[self.account.pk])
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            self.client.post(url)
            r = self.client.post(url, follow=True)
        messages = [str(m) for m in r.context["messages"]]
        self.assertTrue(any("Nothing to record" in m for m in messages), messages)
        self.assertEqual(
            CurrentAccountMovement.objects.filter(movement_type="fx_adjustment").count(), 1)


class FxSweepTest(TestCase):
    """The month-end sweep: the same posting the button makes, for every
    account at once, on the day the period ends."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.euroland = CurrentAccount.objects.create(
            book=self.book, code="ACC-EUR", name="Euroland", type="customer",
            default_currency=self.eur)
        self.dollarland = CurrentAccount.objects.create(
            book=self.book, code="ACC-USD", name="Dollarland", type="customer",
            default_currency=self.usd)
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.10")):
            CurrentAccountMovement.objects.create(
                current_account=self.euroland, book=self.book, date="2026-09-01",
                amount=Decimal("1000.00"), currency=self.eur,
                movement_type="invoice_sale", description="Sale")

    def _run(self, **opts):
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.20")):
            call_command("sweep_fx", stdout=out, **opts)
        return out.getvalue()

    def test_an_ordinary_day_does_nothing(self):
        out = self._run(date="2026-09-15", apply=True)
        self.assertIn("not a month end", out)
        self.assertFalse(CurrentAccountMovement.objects.filter(
            movement_type="fx_adjustment").exists())

    def test_it_says_what_it_would_record_and_writes_nothing(self):
        out = self._run(date="2026-09-30")
        self.assertIn("Euroland", out)
        self.assertIn("Would record 1 difference(s)", out)
        self.assertIn("Nothing was written", out)
        self.assertFalse(CurrentAccountMovement.objects.filter(
            movement_type="fx_adjustment").exists())

    def test_apply_records_on_the_last_day_of_the_month(self):
        out = self._run(date="2026-09-30", apply=True)
        self.assertIn("Recorded 1 difference(s)", out)
        mv = CurrentAccountMovement.objects.get(movement_type="fx_adjustment")
        self.assertEqual(mv.amount, Decimal("100.00"))
        self.assertEqual(str(mv.date), "2026-09-30")

        self.euroland.refresh_from_db()
        self.assertEqual(self.euroland.own_currency_balance(), Decimal("1000.00"))
        self.assertEqual(self.euroland.cached_balance, Decimal("1200.00"))

    def test_running_it_twice_records_once(self):
        self._run(date="2026-09-30", apply=True)
        # The first run closed the gap, so the second finds nothing to take.
        out = self._run(date="2026-09-30", apply=True)
        self.assertIn("Recorded 0 difference(s)", out)
        self.assertEqual(CurrentAccountMovement.objects.filter(
            movement_type="fx_adjustment").count(), 1)

    def test_a_second_run_after_the_rate_moved_again_still_records_once(self):
        """The guard the count above cannot show: the rate moving again on
        the same day would otherwise let a second entry onto the same date,
        and month end is one entry per account by definition."""
        from io import StringIO
        from django.core.management import call_command

        self._run(date="2026-09-30", apply=True)
        out = StringIO()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.40")):
            call_command("sweep_fx", date="2026-09-30", apply=True, stdout=out)
        self.assertIn("already recorded", out.getvalue())
        self.assertEqual(CurrentAccountMovement.objects.filter(
            movement_type="fx_adjustment").count(), 1)

    def test_a_base_currency_account_is_never_touched(self):
        self._run(date="2026-09-30", apply=True)
        self.assertFalse(CurrentAccountMovement.objects.filter(
            current_account=self.dollarland).exists())

    def test_force_records_on_any_day(self):
        out = self._run(date="2026-09-15", apply=True, force=True)
        self.assertIn("Recorded 1 difference(s)", out)
