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
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem


class AnalyticsConvertsForeignOrders(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.product = Product.objects.create(title="Crepe", sku="KZL000901",
                                              price=10, cost=Decimal("0"))
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="KZL000901.1")
        user = User.objects.create_user("an_fx", password="pw")
        self.client.force_login(user)
        self.url = reverse("operating:order_analytics")

    def _order(self, number, **kw):
        order = Order.objects.create(order_number=number, order_status="pending", **kw)
        OrderItem.objects.create(order=order, product=self.product,
                                 product_variant=self.variant,
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


class AnalyticsCostsWhatTheOrderSends(TestCase):
    """Total cost is the rolls held for each line at their own cost, the
    catalog cost only for what nothing covers — as the order page says."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        from operating.models import (
            OrderStockReservation, Warehouse, WarehouseProduct, WarehouseProductItem,
        )
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        product = Product.objects.create(title="Crepe", sku="KZL000902", price=10)
        variant = ProductVariant.objects.create(product=product, variant_sku="KZL000902.1",
                                                variant_cost=Decimal("4.00"))
        order = Order.objects.create(order_number="DK0000910", order_status="pending")
        line = OrderItem.objects.create(order=order, product=product, product_variant=variant,
                                        quantity=Decimal("100"), price=Decimal("10.00"))
        from accounting.models import Book
        warehouse = Warehouse.objects.create(name="W", accounting_book=Book.objects.create(name="B"))
        wp = WarehouseProduct.objects.create(warehouse=warehouse,
                                             name="Crepe", sku="KZL000902.1",
                                             catalog_variant=variant, quantity=Decimal("60"))
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("60"), quantity_remaining=Decimal("60"),
            status="in_stock", unit_cost_base=Decimal("1.00"))
        OrderStockReservation.objects.create(order=order, order_item=line, stock_item=roll,
                                             warehouse_product=wp, quantity=Decimal("60"))
        self.client.force_login(User.objects.create_user("an_cost", password="pw"))

    def test_held_rolls_at_their_cost_the_rest_at_catalog(self):
        # 60 m held at 1.00; the other 40 m at the variant's average, which
        # is now that same held roll's 1.00 — the stock it has on hand.
        summary = self.client.get(reverse("operating:order_analytics")).context["summary"]
        self.assertEqual(summary["total_cost"], 100.0)

    def test_the_order_page_agrees(self):
        from operating.models import Order as O
        self.assertEqual(O.objects.get(order_number="DK0000910").total_cost(), Decimal("100.00"))
