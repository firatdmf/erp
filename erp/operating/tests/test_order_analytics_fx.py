"""Sales analytics adds every order up in base currency.

An order completed in euros carries the rate it was stamped at; an open
one has no stamp yet and floats at today's published rate, the same one
its order page and the ledger use. The page used to read only the stamp
and fall back to one, so an open euro order's euros were counted as
dollars.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import CurrencyCategory
from marketing.models import Product
from operating.models import Order, OrderItem


class AnalyticsConvertsForeignOrders(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.product = Product.objects.create(title="Crepe", sku="KZL000901",
                                              price=10, cost=Decimal("0"))
        user = User.objects.create_user("an_fx", password="pw")
        self.client.force_login(user)
        self.url = reverse("operating:order_analytics")

    def _order(self, number, **kw):
        order = Order.objects.create(order_number=number, order_status="pending", **kw)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("100"), price=Decimal("10.00"))
        return order

    def _revenue(self):
        return self.client.get(self.url).context["summary"]["total_revenue"]

    @patch("accounting.services.get_exchange_rate", return_value=Decimal("1.14"))
    def test_an_open_euro_order_floats_at_the_published_rate(self, _rate):
        self._order("DK0000901", currency=self.eur)
        self.assertEqual(self._revenue(), 1140.0)

    @patch("accounting.services.get_exchange_rate", return_value=Decimal("1.14"))
    def test_a_stamped_rate_wins_over_the_published_one(self, _rate):
        self._order("DK0000902", currency=self.eur, currency_rate=Decimal("1.10"))
        self.assertEqual(self._revenue(), 1100.0)

    def test_an_order_with_no_currency_is_base(self):
        self._order("DK0000903")
        self.assertEqual(self._revenue(), 1000.0)
