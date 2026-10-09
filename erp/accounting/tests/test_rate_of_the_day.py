# to run this test, use the command:
# python manage.py test accounting.tests.test_rate_of_the_day

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounting import services
from accounting.models import CurrencyExchangeRate
from marketing.utils import currency_service


class OneRatePerDayTests(TestCase):
    """A day is converted at one rate, whatever hour the question is asked.

    The reference fix for a day is published that afternoon. Asking for
    "the latest" therefore answered a morning entry with yesterday's fix
    and an evening or backdated one with today's.
    """

    def setUp(self):
        services._RATE_MEMO.clear()

    def test_a_past_day_asks_for_the_fix_of_the_day_before(self):
        sources = services._rate_sources("USD", "EUR", date(2026, 10, 7))

        self.assertEqual(len(sources), 1)
        self.assertIn("/2026-10-06?from=USD&to=EUR", sources[0][0])

    def test_today_asks_for_the_same_fix_morning_or_evening(self):
        today = date.today()
        sources = services._rate_sources("USD", "EUR")

        self.assertIn(f"/{today - timedelta(days=1)}?", sources[0][0])
        self.assertNotIn("latest", sources[0][0])

    def test_only_today_may_fall_back_on_a_latest_only_source(self):
        today = date.today()

        self.assertEqual(len(services._rate_sources("USD", "EUR", today)), 2)
        self.assertEqual(
            len(services._rate_sources("USD", "EUR", today - timedelta(days=1))), 1)

    def test_a_day_that_has_not_come_is_worth_what_today_is(self):
        today = date.today()
        with mock.patch("accounting.services._fetch_rate") as fetch:
            fetch.return_value = Decimal("0.89")
            rate = services.get_exchange_rate(
                "USD", "EUR", on_date=today + timedelta(days=5))

        self.assertEqual(rate, Decimal("0.89"))
        self.assertEqual(fetch.call_args.kwargs["on_date"], today)
        self.assertEqual(
            list(CurrencyExchangeRate.objects.values_list("date", flat=True)), [today])


class LastKnownRateTests(TestCase):
    def setUp(self):
        services._RATE_MEMO.clear()
        self.addCleanup(services._RATE_MEMO.clear)

    def test_the_newest_stored_rate_answers_when_no_source_does(self):
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="TRY", rate=Decimal("48.9"),
            date=date.today() - timedelta(days=9))
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="TRY", rate=Decimal("49.2"),
            date=date.today() - timedelta(days=2))
        with mock.patch("accounting.services._fetch_rate", side_effect=RuntimeError):
            rate = services.last_known_rate("USD", "TRY")

        self.assertEqual(rate, Decimal("49.2"))

    def test_a_pair_the_books_never_held_has_no_rate(self):
        with mock.patch("accounting.services._fetch_rate", side_effect=RuntimeError):
            self.assertIsNone(services.last_known_rate("USD", "RUB"))


class StorefrontRatesWithoutTheLiveSourceTests(TestCase):
    """The storefront prices from the books when its own source is down."""

    def setUp(self):
        services._RATE_MEMO.clear()
        self.addCleanup(services._RATE_MEMO.clear)
        cache = mock.patch.dict(
            currency_service._cache, {"rates": None, "fetched_at": None})
        cache.start()
        self.addCleanup(cache.stop)
        down = mock.patch.object(
            currency_service, "_fetch_live_rates", side_effect=OSError("down"))
        down.start()
        self.addCleanup(down.stop)
        CurrencyExchangeRate.objects.create(
            from_currency="USD", to_currency="TRY", rate=Decimal("49.2"),
            date=date.today() - timedelta(days=2))

    def rates(self):
        with mock.patch("accounting.services._fetch_rate", side_effect=RuntimeError):
            return currency_service.get_rates()

    def test_the_stored_rate_is_used(self):
        self.assertEqual(self.rates(), {"USD": 1.0, "TRY": 49.2})

    def test_a_currency_with_no_rate_gets_no_price(self):
        prices = currency_service.convert_price(Decimal("10"), self.rates())

        self.assertEqual(prices["USD"], 10.0)
        self.assertEqual(prices["TRY"], 492.0)
        self.assertIsNone(prices["EUR"])

    def test_the_rates_endpoint_answers_with_the_same_rates(self):
        with mock.patch("accounting.services._fetch_rate", side_effect=RuntimeError):
            response = self.client.get(reverse("authentication:get_exchange_rates"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rates"], [
            {"currency_code": "USD", "rate": 1.0},
            {"currency_code": "TRY", "rate": 49.2},
        ])
