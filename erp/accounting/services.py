from forex_python.converter import CurrencyRates
from datetime import date
from decimal import Decimal
from .models import CurrencyExchangeRate



c = CurrencyRates()

def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    today = date.today()
    
    # Check cache first, if exists in db, do not fetch again.
    try:
        rate_obj = CurrencyExchangeRate.objects.get(
            from_currency=from_currency,
            to_currency=to_currency,
            date=today
        )
        return rate_obj.rate
    except CurrencyExchangeRate.DoesNotExist:
        # Fetch from forex-python
        try:
            rate_float = c.get_rate(from_currency, to_currency)
            rate = Decimal(str(rate_float))
            # Save to cache
            CurrencyExchangeRate.objects.create(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate
            )
            return rate
        except Exception as e:
            # Handle API failure gracefully
            print(f"Error fetching exchange rate: {e}")
            return None



