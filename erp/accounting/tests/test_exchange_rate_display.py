# to run this test, use the command:
# python manage.py test accounting.test_exchange_rate_display

from decimal import Decimal

import re

from django.test import SimpleTestCase, TestCase

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
    """The card's empty state. Everything about the readings themselves
    goes through the tag in RateDirectionTest, since the template now
    depends on the direction it works out."""

    def test_the_empty_state_still_works(self):
        from django.template.loader import render_to_string
        html = render_to_string(
            "accounting/components/exchange_rates_component.html",
            {"base_currency": None, "rates": []},
        )
        self.assertIn("No exchange rates available.", html)


class RateDirectionTest(TestCase):
    """The card leads with whichever direction reads as a number."""

    def setUp(self):
        from accounting.models import CurrencyCategory
        CurrencyCategory.objects.all().delete()
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")

    def render(self, rates):
        from unittest.mock import patch
        from accounting.templatetags.accounting_tags import exchange_rates_component
        with patch("accounting.services.get_exchange_rate",
                   side_effect=lambda f, t: rates.get(f)):
            with patch("accounting.templatetags.accounting_tags.get_base_currency",
                       return_value=self.usd):
                return exchange_rates_component()

    def short(self, html):
        return re.findall(r'<span class="rate-short">(.*?)</span>', html)

    def test_a_rate_below_one_is_flipped(self):
        """0.02087 USD per lira is true and unreadable; 47.92 lira per
        dollar is how the number is actually thought about."""
        html = self.render({"TRY": Decimal("0.020870"), "EUR": None})
        self.assertEqual(self.short(html), ["1 USD = 47.92 TRY"])

    def test_a_rate_above_one_is_left_alone(self):
        html = self.render({"EUR": Decimal("1.157600"), "TRY": None})
        self.assertEqual(self.short(html), ["1 EUR = 1.16 USD"])

    def test_a_rate_of_exactly_one_is_not_flipped(self):
        html = self.render({"EUR": Decimal("1.000000"), "TRY": None})
        self.assertEqual(self.short(html), ["1 EUR = 1.00 USD"])

    def test_hover_carries_both_directions_at_full_precision(self):
        html = self.render({"TRY": Decimal("0.020870"), "EUR": None})
        full = re.findall(r'<span class="rate-full">(.*?)</span></span>', html, re.S)[0]
        text = re.sub(r"<[^>]+>", "", full).strip()
        self.assertIn("1 USD = 47.915668 TRY", text)
        self.assertIn("1 TRY = 0.02087 USD", text)

    def test_a_zero_rate_is_dropped_rather_than_inverted(self):
        """1/0 has no answer, and neither does the rate."""
        html = self.render({"TRY": Decimal("0"), "EUR": None})
        self.assertEqual(self.short(html), [])
        self.assertIn("No exchange rates available.", html)
