# to run this test, use the command:
# python manage.py test accounting.test_exchange_rate_display

from decimal import Decimal

from django.test import SimpleTestCase

from accounting.templatetags.accounting_tags import format_money, format_rate


class FormatRateTest(SimpleTestCase):
    """A rate is not money — 2dp is right for a balance, wrong here."""

    def test_a_small_rate_keeps_its_precision(self):
        """TRY→USD at 2dp reads 0.02, which implies 50 lira to the dollar
        instead of 47.92."""
        self.assertEqual(format_money(Decimal("0.020870")), "0.02")
        self.assertEqual(format_rate(Decimal("0.020870")), "0.02087")

    def test_trailing_zeros_are_dropped(self):
        self.assertEqual(format_rate(Decimal("1.157600")), "1.1576")

    def test_never_fewer_than_two_decimals(self):
        """So a rate of 1 still looks like a rate."""
        self.assertEqual(format_rate(Decimal("1.000000")), "1.00")
        self.assertEqual(format_rate(Decimal("34.500000")), "34.50")

    def test_thousands_are_separated(self):
        self.assertEqual(format_rate(Decimal("1234.567800")), "1,234.5678")

    def test_full_stored_precision_survives(self):
        self.assertEqual(format_rate(Decimal("0.000123")), "0.000123")

    def test_non_numbers_pass_through(self):
        self.assertEqual(format_rate("n/a"), "n/a")
        self.assertIsNone(format_rate(None))


class ExchangeRatesCardTest(SimpleTestCase):
    """Both readings are rendered; CSS swaps them on hover."""

    def render(self, rate):
        from django.template.loader import render_to_string
        from accounting.models import CurrencyCategory
        return render_to_string(
            "accounting/components/exchange_rates_component.html",
            {
                "base_currency": CurrencyCategory(code="USD", name="US Dollar", symbol="$"),
                "rates": [{
                    "from_currency": CurrencyCategory(code="TRY", name="Turkish Lira", symbol="₺"),
                    "rate": rate,
                }],
            },
        )

    def test_both_readings_are_present(self):
        html = self.render(Decimal("0.020870"))
        self.assertIn('<span class="rate-short">0.02</span>', html)
        self.assertIn('<span class="rate-full">0.02087</span>', html)

    def test_the_item_is_reachable_without_a_mouse(self):
        self.assertIn('tabindex="0"', self.render(Decimal("0.020870")))

    def test_the_empty_state_still_works(self):
        from django.template.loader import render_to_string
        html = render_to_string(
            "accounting/components/exchange_rates_component.html",
            {"base_currency": None, "rates": []},
        )
        self.assertIn("No exchange rates available.", html)
