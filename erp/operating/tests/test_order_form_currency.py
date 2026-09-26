"""Every figure on the order form follows the customer's currency.

The symbol arrives after the customer is picked (operating:customer_currency),
so anything drawn earlier has to be redrawn, and nothing may print a
dollar sign of its own.
"""
import os

from django.test import SimpleTestCase


class TheFormPrintsOneCurrency(SimpleTestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "operating",
                            "partials", "create_order_form.html")
        with open(path, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_no_line_total_is_hard_coded_in_dollars(self):
        self.assertNotIn('>$${', self.src)
        self.assertIn('${CO_CUR.symbol}${(item.quantity*item.price)', self.src)

    def test_the_reprice_redraws_the_totals_and_the_cards(self):
        body = self.src.split("function coRepriceLabels() {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("updateTotal();", body)
        self.assertIn("renderProducts();", body)
        self.assertNotIn("coUpdateTotals", self.src)

    def test_a_retail_sale_goes_back_to_the_books_currency(self):
        body = self.src.split("function coCurrencyFor(type, pk, name) {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("CO_CUR = CO_BASE;", body)
