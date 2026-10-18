"""Cost and profit on an order are said in base, its own currency after.

Almaty keeps its books and its stock in dollars and charges in tenge. A
cost shown only in tenge hid what the goods cost and moved with the rate;
the order's page now reads "$10.00 (₸5,000.00)". An order in dollars reads
as it always did.
"""
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from accounting.models import CurrencyCategory

from operating.templatetags.operating_tags import cost_in_base


def order(code, symbol, rate):
    return SimpleNamespace(currency_code=code, currency_symbol=symbol,
                           rate_to_base=lambda: rate)


class CostInBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        CurrencyCategory.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})

    def test_a_tenge_order_says_dollars_first(self):
        said = str(cost_in_base(Decimal("5000"), order("KZT", "₸", Decimal("0.002"))))
        self.assertEqual(said, '$10.00 <span class="od-in-cur">(₸5,000.00)</span>')

    def test_a_dollar_order_reads_as_before(self):
        self.assertEqual(str(cost_in_base(Decimal("10"), order("USD", "$", Decimal("1")))),
                         "$10.00")

    def test_without_a_rate_it_says_only_what_it_knows(self):
        self.assertEqual(str(cost_in_base(Decimal("5000"), order("KZT", "₸", Decimal("1")))),
                         "₸5,000.00")

    def test_a_loss_keeps_its_sign(self):
        said = str(cost_in_base(Decimal("-500"), order("KZT", "₸", Decimal("0.002"))))
        self.assertTrue(said.startswith("$-1.00"), said)


class TheOrderPage(TestCase):
    """A tenge order's page: cost and profit in dollars, tenge in brackets."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from accounting.models import Book
        from accounting.models_accounts import CurrentAccount
        from crm.models import Company
        from marketing.models import Product
        from operating.models import Order, OrderItem

        usd, _ = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"})
        kzt = CurrencyCategory.objects.create(code="KZT", name="Kazakhstani Tenge", symbol="₸")
        book = Book.objects.create(name="Almaty", base_currency=usd)
        company = Company.objects.create(name="Dana Akhmet")
        account = CurrentAccount.objects.create(
            book=book, code="ACC-KZ", name="Dana Akhmet", type="customer",
            company=company, default_currency=kzt)
        product = Product.objects.create(title="Sheet", featured=False, unit="piece")
        # Fixed as a completed order's would be: ₸1 = $0.002.
        self.order = Order.objects.create(company=company, current_account=account,
                                          currency=kzt, currency_rate=Decimal("0.002"))
        OrderItem.objects.create(order=self.order, product=product,
                                 product_variant=product.variants.create(
                                     variant_sku="SHEET", variant_cost=Decimal("10")),
                                 quantity=Decimal("2"), price=Decimal("10000"))
        user = get_user_model().objects.create_superuser("cib", "c@i.b", "pw")
        user.member.books.add(book)
        self.client.force_login(user)

    def test_cost_and_profit_lead_with_dollars(self):
        from django.urls import reverse
        html = self.client.get(
            reverse("operating:order_detail", kwargs={"pk": self.order.pk})).content.decode()
        # Unit cost $10 = ₸5,000; two of them cost $20; sold for ₸20,000 = $40.
        self.assertIn('$10.00 <span class="od-in-cur">(₸5,000.00)</span>', html)
        self.assertRegex(html, r'data-order-cost[^>]*>\$20\.00 <span class="od-in-cur">\(₸10,000\.00\)')
        self.assertRegex(html, r'data-order-profit[^>]*>\$20\.00 <span class="od-in-cur">\(₸10,000\.00\)')
        self.assertIn("const ORDER_RATE = 0.002", html)
