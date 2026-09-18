# to run this test, use the command:
# python manage.py test operating.tests.test_order_currency

"""An order is priced in its customer's currency, and says so.

Orders used to carry no currency: every price was read as dollars by a
convention recorded in services_accounts._resolve_currency and nowhere the
operator could see. A customer whose account trades in euros was quoted in
euros, stored as dollars and posted to the ledger as dollars — order, print
and balance all agreeing with each other and with nothing the customer had
agreed to.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import (
    _resolve_currency, post_order_movement, stamp_order_currency,
)
from crm.models import Company
from marketing.models import Product
from operating.models import Order, OrderItem


class OrderCurrencyTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.company = Company.objects.create(name="Euroland")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-EUR", name="Euroland", type="customer",
            company=self.company, default_currency=self.eur,
        )
        self.product = Product.objects.create(title="Krep", sku="KRP", featured=False)
        self.member = getattr(
            get_user_model().objects.create_superuser("firat_cur", "a@b.c", "pw"), "member", None)

    def _order(self, account=None, price="2.00", qty="700"):
        order = Order.objects.create(company=self.company,
                                     current_account=account or self.account)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal(qty), price=Decimal(price))
        return order

    # ── What the order is in ────────────────────────────────────────
    def test_it_takes_the_customers_currency_and_the_rate_of_the_day(self):
        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        order.refresh_from_db()
        self.assertEqual(order.currency, self.eur)
        self.assertEqual(order.currency_rate, Decimal("1.08"))
        self.assertEqual(order.currency_code, "EUR")
        self.assertEqual(order.currency_symbol, "€")

    def test_an_order_with_no_currency_is_still_dollars(self):
        order = self._order()
        self.assertIsNone(order.currency_id)
        self.assertEqual(order.currency_code, "USD")
        self.assertEqual(order.currency_symbol, "$")
        self.assertEqual(_resolve_currency(order), self.usd)

    def test_a_dollar_account_needs_no_rate(self):
        usd_account = CurrentAccount.objects.create(
            book=self.book, code="C-USD", name="Dollarland", type="customer",
            default_currency=self.usd)
        order = self._order(account=usd_account)
        stamp_order_currency(order, usd_account)
        order.refresh_from_db()
        self.assertEqual(order.currency, self.usd)
        self.assertIsNone(order.currency_rate)

    def test_the_currency_is_settled_once_and_not_restated_later(self):
        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        # Something later stamps it again — a customer swapped on the order
        # screen, a re-post, a backfill. The price on the line has not
        # changed, so what it is in must not change either.
        usd_account = CurrentAccount.objects.create(
            book=self.book, code="C-USD2", name="Dollarland", type="customer",
            default_currency=self.usd)
        stamp_order_currency(order, usd_account)
        order.refresh_from_db()
        self.assertEqual(order.currency, self.eur)
        self.assertEqual(order.currency_rate, Decimal("1.08"))

    # ── What the ledger posts ───────────────────────────────────────
    def test_a_euro_order_posts_euros_converted_at_its_own_rate(self):
        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
            post_order_movement(order, member=self.member)

        mv = CurrentAccountMovement.objects.get(current_account=self.account,
                                                movement_type="order_sale")
        self.assertEqual(mv.currency, self.eur)
        self.assertEqual(mv.amount, Decimal("1400.00"))          # 700 × 2.00
        self.assertEqual(mv.exchange_rate, Decimal("1.08000000"))
        self.assertEqual(mv.amount_base, Decimal("1512.00"))     # 1400 × 1.08

    def test_an_order_with_no_currency_posts_dollars_as_it_always_did(self):
        order = self._order()
        post_order_movement(order, member=self.member)
        mv = CurrentAccountMovement.objects.get(current_account=self.account,
                                                movement_type="order_sale")
        self.assertEqual(mv.currency, self.usd)
        self.assertEqual(mv.amount, Decimal("1400.00"))
        self.assertEqual(mv.amount_base, Decimal("1400.00"))

    # ── What the book records ───────────────────────────────────────
    def test_the_order_converts_itself_into_base_for_the_book(self):
        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        order.refresh_from_db()
        self.assertEqual(order.total_value(), Decimal("1400.00"))       # shown: €
        self.assertEqual(order.total_value_base(), Decimal("1512.00"))  # booked: $
        self.assertEqual(order.rate_to_base(), Decimal("1.08"))

    def test_an_order_in_base_needs_no_crossing(self):
        order = self._order()
        self.assertEqual(order.rate_to_base(), Decimal("1"))
        self.assertEqual(order.total_value_base(), order.total_value())

    def test_cost_is_stated_in_the_orders_currency_so_margin_is_not_mixed(self):
        # The catalog keeps cost in base: $1.08 a unit.
        self.product.cost = Decimal("1.08")
        self.product.save(update_fields=["cost"])
        order = self._order(price="2.00", qty="100")
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        order.refresh_from_db()
        line = order.items.get()
        # $1.08 is €1.00, so a €2.00 price earns €1.00 — not €0.92, which is
        # what subtracting the dollar figure from the euro one would give.
        self.assertEqual(line.unit_cost_base(), Decimal("1.08"))
        self.assertEqual(line.unit_cost(), Decimal("1.0000"))
        self.assertEqual(line.line_cost(), Decimal("100.00"))
        self.assertEqual(line.gross_profit(), Decimal("100.00"))

    def test_the_snapshot_records_what_its_figures_are_in(self):
        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        order.refresh_from_db()
        self.assertEqual(order.build_snapshot()["currency_code"], "EUR")
        order.original_snapshot = order.build_snapshot()
        self.assertEqual(order.snapshot_currency_symbol, "€")

    # ── What the customer's invoice says ────────────────────────────
    def test_the_invoice_follows_the_order_not_the_account(self):
        from accounting.invoice_doc import build_order_doc

        order = self._order()
        with patch("accounting.services.get_exchange_rate", return_value=Decimal("1.08")):
            stamp_order_currency(order, self.account)
        doc = build_order_doc(order)
        self.assertEqual(doc.currency_code, "EUR")
        self.assertEqual(doc.currency_symbol, "€")

        # An order raised under the old convention still invoices in dollars,
        # whatever the account trades in today.
        legacy = self._order()
        self.assertEqual(build_order_doc(legacy).currency_code, "USD")
