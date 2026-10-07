"""The suite's runner, named by TEST_RUNNER in settings.

Its one job beyond Django's default is to put the Bunny CDN out of
reach for the length of a run.

Creating an order uploads a QR code, so most of the operating suite
touches the CDN, and nearly every one of those tests already carries an
@patch for it — on setUp, where the patch lifts the moment setUp
returns and the test body goes to the real network. On a developer's
machine that looked like it worked: .env holds a live
BUNNY_STORAGE_API_KEY, so the upload really did succeed, against
production storage. CI has no key, so the upload 401s, order creation
aborts, and twenty-eight tests fail for a reason that has nothing to do
with what any of them assert.

One stub here fixes all of them and stops the next one happening. A
test that wants to watch an upload FAIL still patches it itself; an
inner patch wins over this one and is restored to this one on exit.

The exchange-rate services are kept out of reach the same way, and for
the same reason. Any row in a currency other than its book's asks for
the day's rate, and two dozen accounting tests got theirs from whichever
public API answered — so they passed wherever one did and failed, for
nothing they assert, wherever none did. They get a fixed table instead.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test.runner import DiscoverRunner

# What one unit is worth in dollars. Roughly true, so a test that only
# says "300 lira is well under 50 dollars" still means something; a test
# about a particular rate states its own (CurrencyExchangeRate, or a
# patch of its own over this one).
_IN_DOLLARS = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.16"),
    "GBP": Decimal("1.33"),
    "TRY": Decimal("0.024"),
    "KZT": Decimal("0.002"),
}


def _fixed_rate(from_currency, to_currency, on_date=None):
    """Stands in for accounting.services._fetch_rate: the same rate on
    every day, and the same failure for a currency nobody publishes."""
    fc, tc = (from_currency or "").upper(), (to_currency or "").upper()
    if fc not in _IN_DOLLARS or tc not in _IN_DOLLARS:
        raise RuntimeError(f"no FX source returned {fc}->{tc} (tests are offline)")
    return (_IN_DOLLARS[fc] / _IN_DOLLARS[tc]).quantize(Decimal("0.000001"))


class NoCdnTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        patcher = patch("marketing.utils.bunny_storage.upload_to_bunny",
                        return_value="https://mock-cdn.invalid/test.png")
        # WhatsApp too: nothing in the suite may reach Meta, whatever a
        # test has configured.
        whatsapp = patch("operating.order_whatsapp._post",
                         side_effect=AssertionError("WhatsApp is off limits in tests"))
        rates = patch("accounting.services._fetch_rate", side_effect=_fixed_rate)
        patcher.start()
        whatsapp.start()
        rates.start()
        try:
            return super().run_tests(*args, **kwargs)
        finally:
            rates.stop()
            whatsapp.stop()
            patcher.stop()
