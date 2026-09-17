"""The price a sales rep sees in place of a cost: cost × 1.10, rounded UP
to the next 0.05. Derived every time it is shown; nothing stores it."""
from decimal import Decimal

from django.test import SimpleTestCase

from erp.roles import sales_rep_price


class SalesRepPrice(SimpleTestCase):
    def test_marks_up_and_rounds_up_to_the_next_five_cents(self):
        self.assertEqual(sales_rep_price(Decimal("0.68")), Decimal("0.75"))   # 0.748
        self.assertEqual(sales_rep_price(Decimal("2.40")), Decimal("2.65"))   # 2.64

    def test_a_price_already_on_a_step_stays_put(self):
        self.assertEqual(sales_rep_price(Decimal("1")), Decimal("1.10"))
        self.assertEqual(sales_rep_price(Decimal("18.70")), Decimal("20.60"))  # 20.57 → up

    def test_never_rounds_down(self):
        self.assertEqual(sales_rep_price(Decimal("2.7280")), Decimal("3.05"))  # 3.0008

    def test_no_cost_is_no_price(self):
        self.assertIsNone(sales_rep_price(None))
