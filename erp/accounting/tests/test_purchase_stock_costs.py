"""What a received purchase's stock is valued at.

Every book's base is USD, and the stock account is built from each item's
USD cost. A price in another currency is converted when the goods arrive —
at the rates the receipt showed, which are the ones its invoice is booked
at, and otherwise at the day's published rate. A currency with no rate at
all is refused: the old fallback of 1 valued lira as dollars.

Run with:
    python manage.py test accounting.tests.test_purchase_stock_costs
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem
from operating.views_warehouse import _PurchaseRates

PUBLISHED = {("TRY", "USD"): Decimal("0.025"), ("USD", "TRY"): Decimal("40"),
             ("EUR", "USD"): Decimal("1.10"), ("EUR", "TRY"): Decimal("44")}


def _published(source, target, on_date=None):
    return PUBLISHED.get((source, target))


@patch("accounting.services.get_exchange_rate", side_effect=_published)
class RatesTest(SimpleTestCase):
    def test_the_receipts_own_rates_come_first(self, _fx):
        rates = _PurchaseRates("USD", {"TRY": "0.02"})
        self.assertEqual(rates.costs(Decimal("100"), "TRY"),
                         (Decimal("2.0000"), Decimal("100.0000")))

    def test_a_lira_account_values_a_dollar_price_at_the_receipts_rate(self, _fx):
        # Billing in TRY, a USD line at 41 on the page: $3 is ₺123.
        rates = _PurchaseRates("TRY", {"USD": "41"})
        self.assertEqual(rates.costs(Decimal("3"), "USD"),
                         (Decimal("3.0000"), Decimal("123.0000")))

    def test_the_published_rate_fills_what_the_receipt_did_not_show(self, _fx):
        rates = _PurchaseRates("TRY", {})
        self.assertEqual(rates.costs(Decimal("100"), "TRY"),
                         (Decimal("2.5000"), Decimal("100.0000")))

    def test_euros_are_converted_not_passed_off_as_dollars(self, _fx):
        self.assertEqual(_PurchaseRates().costs(Decimal("10"), "EUR"),
                         (Decimal("11.0000"), Decimal("440.0000")))

    def test_no_rate_is_no_cost_never_parity(self, _fx):
        rates = _PurchaseRates()
        self.assertIsNone(rates.rate("GBP", "USD"))
        self.assertEqual(rates.costs(Decimal("5"), "GBP"), (None, None))

    def test_a_free_item_has_no_cost_to_convert(self, _fx):
        self.assertEqual(_PurchaseRates().costs(Decimal("0"), "TRY"), (None, None))


class ReceivedLiraPurchaseTest(TestCase):
    def setUp(self):
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="₺")
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-KZL", name="Kızılırmak", type="supplier",
            default_currency=self.try_)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        admin = get_user_model().objects.create_superuser("lira_buyer", "l@b.t", "pw")
        self.client.force_login(admin)

    @patch("marketing.utils.bunny_storage.upload_to_bunny",
           return_value="https://mock-cdn.net/qr.png")
    def _receive(self, _upload, currency="TRY", rates=None):
        order = self.client.post(
            reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
            data=json.dumps({
                "warehouse_id": self.wh.pk, "current_account_id": self.account.pk,
                "date": "2026-09-17", "rates": rates or {},
                "products": [{
                    "main_product": {"mode": "new", "name": "GREK", "sku": "GRK77"},
                    "unit": "mt", "has_variants": True,
                    "variants": [{"name": "Beyaz", "sku": "GRK77.B", "price": "100",
                                  "currency": currency, "tops": [{"qty": 20, "barcode": "KZL-1"}]}],
                }],
            }), content_type="application/json")
        invoice_id = order.json()["invoice_id"]
        return invoice_id, self.client.post(
            reverse("accounts:purchase_order_confirm", args=[invoice_id])).json()

    @patch("accounting.services.get_exchange_rate", side_effect=_published)
    def test_lira_stock_is_valued_in_dollars_at_the_days_rate(self, _fx):
        _id, confirm = self._receive()
        self.assertTrue(confirm["success"], confirm)
        wp = WarehouseProduct.objects.get(sku="GRK77.B")
        self.assertEqual((wp.purchase_price, wp.purchase_currency), (Decimal("100.00"), "TRY"))
        self.assertEqual((wp.cost_usd, wp.cost_try), (Decimal("2.5000"), Decimal("100.0000")))
        self.assertEqual(WarehouseProductItem.objects.get(barcode="KZL-1").unit_cost_base,
                         Decimal("2.5000"))

    @patch("accounting.services.get_exchange_rate", side_effect=_published)
    def test_a_dollar_price_uses_the_rate_the_invoice_was_booked_at(self, _fx):
        invoice_id, confirm = self._receive(currency="USD", rates={"USD": "41"})
        self.assertTrue(confirm["success"], confirm)
        wp = WarehouseProduct.objects.get(sku="GRK77.B")
        self.assertEqual((wp.cost_usd, wp.cost_try), (Decimal("100.0000"), Decimal("4100.0000")))
        # The invoice booked ₺4,100 a metre — the same rate.
        self.assertEqual(Invoice.objects.get(pk=invoice_id).items.get().unit_price,
                         Decimal("4100.000000"))

    @patch("accounting.services.get_exchange_rate", return_value=None)
    def test_no_rate_to_dollars_refuses_the_receipt(self, _fx):
        _id, confirm = self._receive()
        self.assertFalse(confirm["success"])
        self.assertIn("TRY", confirm["error"])
        self.assertFalse(WarehouseProductItem.objects.filter(barcode="KZL-1").exists())
