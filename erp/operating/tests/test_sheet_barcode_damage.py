"""A barcode column Excel left as a number is read back as far as it can be.

Excel treats a barcode cell as a number unless the column is formatted as
Text. A whole number can come back as 8690000000123.0, which matches
nothing; leading zeros are gone for good ("000508345" → 508345). The import
puts the ".0" back the way it came and says so about the zeros — the row
still imports, because a short code may be a real internal one.

Run with:
    python manage.py test operating.tests.test_sheet_barcode_damage
"""
from django.test import SimpleTestCase

from operating.views_warehouse import _sheet_barcode


class TheBarcodeCellIsReadAsWritten(SimpleTestCase):
    def test_a_whole_number_loses_its_decimal_tail(self):
        for value in (8690000000123.0, "8690000000123.0", 8690000000123):
            self.assertEqual(_sheet_barcode(value), ("8690000000123", None))

    def test_a_full_length_barcode_passes_untouched(self):
        self.assertEqual(_sheet_barcode("712179794948"), ("712179794948", None))
        self.assertEqual(_sheet_barcode(" 2000037564405 "), ("2000037564405", None))

    def test_a_short_all_digit_code_is_flagged_but_kept(self):
        barcode, warning = _sheet_barcode(508345)
        self.assertEqual(barcode, "508345")
        self.assertIn("Excel", warning)

    def test_a_code_with_letters_is_not_this_checks_business(self):
        self.assertEqual(_sheet_barcode("ABC-12"), ("ABC-12", None))

    def test_an_empty_cell_stays_empty(self):
        self.assertEqual(_sheet_barcode(None), (None, None))
        self.assertEqual(_sheet_barcode("  "), ("", None))
