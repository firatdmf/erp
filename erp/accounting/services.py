import requests
from datetime import date, datetime, timedelta
from decimal import Decimal
from .models import CurrencyExchangeRate


def _rate_sources(fc: str, tc: str, on_date=None) -> list:
    """Where to ask for the rate of `on_date`, best first: (url, picker)."""
    today = date.today()
    on_date = _as_date(on_date) or today
    fix_day = (on_date - timedelta(days=1)).isoformat()
    sources = [
        (f"https://api.frankfurter.dev/v1/{fix_day}?from={fc}&to={tc}",
         lambda j: j.get("rates", {}).get(tc)),
    ]
    if on_date >= today:
        # Only publishes the latest rate, so it can stand in for today
        # and for no other day.
        sources.append(
            (f"https://open.er-api.com/v6/latest/{fc}",
             lambda j: j.get("rates", {}).get(tc)))
    return sources


def _fetch_rate(from_currency: str, to_currency: str, on_date=None) -> Decimal:
    """Fetch the rate that applies on `on_date` (today when not given).

    The old implementation scraped Google Finance for a `data-last-price="`
    marker; Google removed that marker, so every call raised
    "substring not found". These APIs return clean JSON and don't break on
    HTML changes.

    A day has one rate: the reference fix that was already published when
    the day began, which is the one from the last trading day before it.
    The fix for a day only comes out that afternoon, so asking for "the
    latest" gave a morning entry yesterday's fix and an evening or
    backdated one today's — two rates for one day, and the two directions
    of a pair disagreeing with each other. Asking for the day before
    answers the same at any hour, on the day or a year later.

    A day before with no published rate — a weekend, a holiday — resolves
    to the most recent trading day before it.
    """
    fc, tc = (from_currency or "").upper(), (to_currency or "").upper()
    if not fc or not tc:
        raise ValueError("currency missing")
    if fc == tc:
        return Decimal("1")

    sources = _rate_sources(fc, tc, on_date)
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
    Every entry of one day gets the same rate, whatever hour it is asked
    for (see `_fetch_rate`).
    Rates are cached per (pair, day), so asking for an old day repeatedly
    costs one fetch ever.
    """
    # A day that has not come yet has no rate of its own; it is worth
    # what today is, and is not filed under a date that may still change.
    day = min(_as_date(on_date) or date.today(), date.today())
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


def last_known_rate(from_currency: str, to_currency: str):
    """Today's rate, or failing that the newest one the books hold.

    For a caller that has to show a price whether or not a rate source is
    answering: a rate a few days old is close, and a made-up one is not.
    None when the books have never held this pair.
    """
    rate = get_exchange_rate(from_currency, to_currency)
    if rate:
        return rate
    row = (CurrencyExchangeRate.objects
           .filter(from_currency=from_currency, to_currency=to_currency)
           .order_by("-date")
           .first())
    return row.rate if row else None
