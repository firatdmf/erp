# to run this test, use the command:
# python manage.py test accounting.test_cari_detail_fx

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement


class CariDetailConversionTests(TestCase):
    """A converted row has to say what it came to, and at what rate.

    The account page showed "-939.70 TRY" against a balance that moved by
    19.54 with nothing connecting them — which is exactly the question it
    then could not answer. The statement had said this for a while; this is
    the same fact on the page the statement is reached from.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cdfx", password="pw"
        )
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.cari = CariAccount.objects.create(
            book=self.book, code="FIRAT", name="MUHAMMED FIRAT ÖZTÜRK",
            type="customer", default_currency=self.usd,
        )

    def _movement(self, amount, currency, rate=None, base=None):
        mv = CariMovement(
            cari=self.cari, book=self.book, date="2026-08-26",
            amount=Decimal(amount), currency=currency,
            movement_type="adjustment", description="stopaj",
        )
        if rate is not None:
            mv.exchange_rate = Decimal(rate)
            mv.amount_base = Decimal(base)
        mv.save()
        return mv

    def _page(self):
        return self.client.get(
            reverse("accounts:detail", kwargs={"pk": self.cari.pk})
        )

    def test_a_converted_row_states_its_base_value_and_rate(self):
        self._movement("-939.70", self.try_, rate="0.020790", base="-19.54")

        html = self._page().content.decode()

        self.assertIn('<span class="cd-fx">', html)
        self.assertIn("939.70", html)
        self.assertIn("19.54", html)
        # format_rate drops trailing zeros — 0.020790 reads 0.02079.
        self.assertIn("0.02079", html)

    def test_the_figure_shown_is_the_one_the_balance_moved_by(self):
        """Read off the stored row, not recomputed — 939.70 x 0.020790 is
        19.5364, and a page that recomputed would print 19.54 or 19.53
        depending on how it rounded, with no guarantee of matching."""
        mv = self._movement("-939.70", self.try_, rate="0.020790", base="-19.54")
        self.cari.refresh_from_db()

        html = self._page().content.decode()

        self.assertEqual(mv.amount_base, Decimal("-19.54"))
        self.assertEqual(self.cari.cached_balance, Decimal("-19.54"))
        self.assertIn("19.54", html)

    def test_a_base_currency_row_says_nothing_extra(self):
        """A rate of 1 beside a repeated figure tells the reader nothing."""
        self._movement("-100.00", self.usd)

        html = self._page().content.decode()

        self.assertIn("100.00", html)
        # The rendered span, not the class name — the page's own stylesheet
        # defines .cd-fx whether or not any row uses it.
        self.assertNotIn('<span class="cd-fx">', html)
