import requests
from datetime import date, datetime
from decimal import Decimal
from .models import CurrencyExchangeRate


def _fetch_rate(from_currency: str, to_currency: str, on_date=None) -> Decimal:
    """Fetch an FX rate from reliable JSON APIs (with fallback).

    The old implementation scraped Google Finance for a `data-last-price="`
    marker; Google removed that marker, so every call raised
    "substring not found". These APIs return clean JSON and don't break on
    HTML changes.

    `on_date` asks for the rate as it stood that day. A transaction entered
    late is still worth what it was worth when it happened, so a backdated
    row must not be converted at today's rate. Sources that only publish the
    latest rate are skipped for a dated request rather than answering it
    with the wrong day's number.

    A date with no published rate — a weekend, a holiday — resolves to the
    most recent trading day before it, which is what the money was worth.
    """
    fc, tc = (from_currency or "").upper(), (to_currency or "").upper()
    if not fc or not tc:
        raise ValueError("currency missing")
    if fc == tc:
        return Decimal("1")

    on_date = _as_date(on_date)
    if on_date and on_date < date.today():
        day = on_date.isoformat()
        sources = (
            (f"https://api.frankfurter.app/{day}?from={fc}&to={tc}",
             lambda j: j.get("rates", {}).get(tc)),
            (f"https://api.exchangerate.host/{day}?base={fc}&symbols={tc}",
             lambda j: j.get("rates", {}).get(tc)),
        )
    else:
        sources = (
            (f"https://api.frankfurter.app/latest?from={fc}&to={tc}",
             lambda j: j.get("rates", {}).get(tc)),
            (f"https://open.er-api.com/v6/latest/{fc}",
             lambda j: j.get("rates", {}).get(tc)),
            (f"https://api.exchangerate.host/latest?base={fc}&symbols={tc}",
             lambda j: j.get("rates", {}).get(tc)),
        )
    last_err = None
    for url, pick in sources:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            val = pick(resp.json())
            if val:
                return Decimal(str(val))
        except Exception as exc:  # try the next source
            last_err = exc
            continue
    raise RuntimeError(f"no FX source returned {fc}->{tc} ({last_err})")


# Process-level memo so a single request that needs the rate for hundreds of
# products (e.g. a warehouse value rollup) doesn't hit the DB/API once per
# product. Keyed by (from, to, day); cleared naturally when the worker restarts.
_RATE_MEMO = {}


def _as_date(value):
    """Coerce to a date, because callers hand over both kinds.

    A model field assigned "2026-08-17" holds the string until the instance
    is reloaded, so a date reaching here from an unsaved row is as likely to
    be text as a date. It used to be compared against date.today() as-is,
    which raises TypeError, which was caught as "no source had the rate" —
    the conversion then failed for a reason that had nothing to do with FX.
    """
    if isinstance(value, str):
        from django.utils.dateparse import parse_date

        return parse_date(value)
    if isinstance(value, datetime):
        return value.date()
    return value


def get_exchange_rate(from_currency: str, to_currency: str, on_date=None) -> Decimal:
    """The rate from one currency to another, on a given day.

    Defaults to today. Pass the transaction's own date to convert a
    backdated entry at what the money was worth then rather than now.
    Rates are cached per (pair, day), so asking for an old day repeatedly
    costs one fetch ever.
    """
    day = _as_date(on_date) or date.today()
    ck = (from_currency, to_currency, day)
    if ck in _RATE_MEMO:
        return _RATE_MEMO[ck]

    # Per-day DB cache (filter().first() tolerates accidental duplicate rows).
    rate_obj = (CurrencyExchangeRate.objects
                .filter(from_currency=from_currency, to_currency=to_currency, date=day)
                .first())
    if rate_obj is not None:
        _RATE_MEMO[ck] = rate_obj.rate
        return rate_obj.rate

    try:
        rate = _fetch_rate(from_currency, to_currency, on_date=day)
        CurrencyExchangeRate.objects.create(
            from_currency=from_currency, to_currency=to_currency,
            rate=rate, date=day,
        )
        _RATE_MEMO[ck] = rate
        return rate
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "FX rate %s->%s failed: %s", from_currency, to_currency, e)
        _RATE_MEMO[ck] = None   # don't re-hammer the API for this process
        return None


