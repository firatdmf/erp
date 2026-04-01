import httpx
from datetime import date
from decimal import Decimal
from .models import CurrencyExchangeRate, CashTransactionEntry
from .views import get_total_base_currency_balance


def _fetch_rate_from_google(from_currency: str, to_currency: str) -> Decimal:
    """Fetch exchange rate from Google Finance."""
    url = f"https://www.google.com/finance/quote/{from_currency}-{to_currency}"
    response = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    response.raise_for_status()
    # The rate is in a div with data-last-price attribute
    text = response.text
    marker = 'data-last-price="'
    start = text.index(marker) + len(marker)
    end = text.index('"', start)
    return Decimal(text[start:end])


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
            rate = _fetch_rate_from_google(from_currency, to_currency)
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
