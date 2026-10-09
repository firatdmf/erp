"""
currency_service.py

In-memory cached currency conversion service for the marketing app.
Fetches exchange rates from open.er-api.com at most once per hour.
Does NOT persist rates to the database. When that source is down it
answers with the rates the books hold.
"""

import time
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache: shared across all requests within the same Django process.
# ---------------------------------------------------------------------------
_cache = {
    "rates": None,       # dict[str, float] | None
    "fetched_at": None,  # float (time.time()) | None
}

CACHE_TTL_SECONDS = 3600  # 1 hour
API_URL = "https://open.er-api.com/v6/latest/USD"
SUPPORTED_CURRENCIES = ["USD", "TRY", "EUR", "RUB", "PLN"]

def _is_cache_valid() -> bool:
    if _cache["rates"] is None or _cache["fetched_at"] is None:
        return False
    return (time.time() - _cache["fetched_at"]) < CACHE_TTL_SECONDS


def _fetch_live_rates() -> dict:
    """Fetch rates from the external API. Returns a rates dict or raises."""
    with urllib.request.urlopen(API_URL, timeout=5) as response:
        data = json.loads(response.read().decode())
    if data.get("result") != "success" and "rates" not in data:
        raise ValueError(f"Unexpected API response: {data}")
    raw = data["rates"]
    return {code: float(raw[code]) for code in SUPPORTED_CURRENCIES if code in raw}


def _rates_from_books() -> dict:
    """The rates accounting holds, for when the live source is down.

    A currency the books have never converted is left out rather than
    guessed at.
    """
    from accounting.services import last_known_rate

    rates = {"USD": 1.0}
    for code in SUPPORTED_CURRENCIES:
        if code == "USD":
            continue
        try:
            rate = last_known_rate("USD", code)
        except Exception as exc:
            logger.warning("[currency_service] No stored rate for %s (%s).", code, exc)
            rate = None
        if rate:
            rates[code] = float(rate)
    return rates


def get_rates() -> dict:
    """
    Return a dict of {currency_code: float} for all supported currencies.
    Uses in-memory cache; refreshes from API if cache is older than 1 hour.
    Falls back to the rates the books hold on error, which may leave a
    currency out.
    """
    global _cache

    if _is_cache_valid():
        return _cache["rates"]

    try:
        rates = _fetch_live_rates()
        _cache["rates"] = rates
        _cache["fetched_at"] = time.time()
        logger.info("[currency_service] Rates refreshed from API: %s", rates)
        return rates
    except Exception as exc:
        logger.warning("[currency_service] Failed to fetch live rates (%s). Using fallback.", exc)
        # If we have stale cache, prefer it over the books' daily rate
        if _cache["rates"] is not None:
            logger.info("[currency_service] Using stale cache.")
            return _cache["rates"]
        logger.info("[currency_service] Using the rates the books hold.")
        return _rates_from_books()


def convert_price(price_usd, rates: dict) -> dict:
    """
    Given a price in USD and a rates dict, return a dict of converted prices
    for all supported currencies, rounded to 2 decimal places.

    Args:
        price_usd: numeric price (int, float, Decimal, or None)
        rates: output of get_rates()

    Returns:
        {"USD": 10.0, "TRY": 360.0, "EUR": 9.2, "RUB": 900.0, "PLN": 41.0}
    """
    if price_usd is None:
        return {code: None for code in SUPPORTED_CURRENCIES}
    try:
        usd = float(price_usd)
    except (TypeError, ValueError):
        return {code: None for code in SUPPORTED_CURRENCIES}

    # A currency with no rate gets no price: multiplying by a stand-in
    # would publish the dollar figure under another currency's name.
    return {
        code: round(usd * rates[code], 2) if rates.get(code) else None
        for code in SUPPORTED_CURRENCIES
    }
