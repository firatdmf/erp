import requests
from datetime import date
from decimal import Decimal
from .models import CurrencyExchangeRate, CashTransactionEntry
from .views import get_total_base_currency_balance


def _fetch_rate(from_currency: str, to_currency: str) -> Decimal:
    """Fetch an FX rate from reliable JSON APIs (with fallback).

    The old implementation scraped Google Finance for a `data-last-price="`
    marker; Google removed that marker, so every call raised
    "substring not found". These APIs return clean JSON and don't break on
    HTML changes."""
    fc, tc = (from_currency or "").upper(), (to_currency or "").upper()
    if not fc or not tc:
        raise ValueError("currency missing")
    if fc == tc:
        return Decimal("1")

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


def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    today = date.today()

    # Check cache first, if exists in db, do not fetch again.
    try:
        rate_obj = CurrencyExchangeRate.objects.get(
            from_currency=from_currency, to_currency=to_currency, date=today
        )
        print(f"from {from_currency} to {to_currency} rate is: {rate_obj.rate} ")
        return rate_obj.rate
    except CurrencyExchangeRate.DoesNotExist:
        try:
            rate = _fetch_rate(from_currency, to_currency)
            print(f"from {from_currency} to {to_currency} rate is: {rate} ")
            # Save to cache
            CurrencyExchangeRate.objects.create(
                from_currency=from_currency, to_currency=to_currency, rate=rate
            )
            return rate
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
            return None


def update_cash_transaction_entry_total_base_currency_balance(book_pk):
    total = get_total_base_currency_balance(book_pk)
    cash_transaction_entry = CashTransactionEntry.objects.filter(book=book_pk).latest(
        "pk"
    )
    cash_transaction_entry.total_base_currency_balance = total
    cash_transaction_entry.save(update_fields=["total_base_currency_balance"])
    return total
