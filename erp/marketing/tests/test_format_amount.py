"""A quantity as a label prints it: a count whole, a length to the centimeter."""
from decimal import Decimal

from django.test import SimpleTestCase

from marketing.units import format_amount


class FormatAmount(SimpleTestCase):
    def test_a_count_prints_whole(self):
        self.assertEqual(format_amount(Decimal("80.00"), "piece"), "80 pcs")

    def test_meters_keep_their_centimeters(self):
        self.assertEqual(format_amount(Decimal("19.70"), "m"), "19.70 m")
        self.assertEqual(format_amount(Decimal("20"), "m"), "20.00 m")

    def test_a_part_of_a_count_is_not_rounded_away(self):
        self.assertEqual(format_amount(Decimal("1.50"), "pack"), "1.50 pack")

    def test_thousands_are_grouped(self):
        self.assertEqual(format_amount(Decimal("1234.5"), "m"), "1,234.50 m")
