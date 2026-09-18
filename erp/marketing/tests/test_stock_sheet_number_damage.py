"""A stock sheet whose codes Excel turned into numbers says so.

Excel reads "3010.140" as the decimal 3010.14 and "0000103" as 103, so a
CSV opened and saved in Excel arrives with codes that match nothing. The
comparison used to list them among the not-found and leave it there. It now
names them and points at the SKU each most likely came from.

Our own .xlsx downloads are not the problem — openpyxl writes SKUs as text,
and their cells carry Excel's Text format (erp.xlsx_utils.TEXT) so a retyped
one stays text.

Run with:
    python manage.py test marketing.tests.test_stock_sheet_number_damage
"""
from django.test import TestCase

from marketing.models import Product, ProductVariant
from marketing.views_csv_stock import _codes_excel_turned_into_numbers


class TheCodesExcelDamaged(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="Krep", sku="3010")
        ProductVariant.objects.create(product=self.product, variant_sku="3010.140")
        ProductVariant.objects.create(product=self.product, variant_sku="3010.1400")
        Product.objects.create(title="Tül", sku="0000103")

    def test_a_dropped_trailing_zero_points_at_the_skus_it_could_be(self):
        self.assertEqual(
            _codes_excel_turned_into_numbers(["3010.14"]),
            [{"code": "3010.14", "likely": ["3010.140", "3010.1400"]}])

    def test_a_dropped_leading_zero_points_at_its_sku(self):
        self.assertEqual(
            _codes_excel_turned_into_numbers(["103"]),
            [{"code": "103", "likely": ["0000103"]}])

    def test_a_code_that_reads_as_a_number_but_matches_nothing_is_left_alone(self):
        self.assertEqual(_codes_excel_turned_into_numbers(["9999.99", "777"]), [])

    def test_codes_that_are_not_numbers_are_not_this_checks_business(self):
        self.assertEqual(
            _codes_excel_turned_into_numbers(["K24644.BEYAZ-140", "3010.G07", ""]),
            [])

    def test_an_intact_code_is_never_flagged(self):
        # 3010.140 matches a variant, so it never reaches this check — but
        # even passed in, it must not be read as damage to itself.
        self.assertEqual(_codes_excel_turned_into_numbers(["3010.140"]),
                         [{"code": "3010.140", "likely": ["3010.1400"]}])
