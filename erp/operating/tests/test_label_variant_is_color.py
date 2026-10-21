"""The variant part of a roll label is its colour, never a "model".

A label's variant part is either a colour word ("GÜMÜŞ") or the mill's
colourway code ("V-356", "G93"). Codes used to be stored as a separate
"model" attribute, which the storefront could not filter on and which
ended up holding colour words too. Now both are the colour: the word by
its English key, the code as printed.

Run with:
    python manage.py test operating.tests.test_label_variant_is_color
"""
from django.test import TestCase

from operating.catalog_sync import derive_catalog, parse_label_name


class LabelVariantIsColorTest(TestCase):
    def test_a_colour_word_is_translated(self):
        cat = derive_catalog("MRK00047", "MT-3016 GÜMÜŞ")
        self.assertEqual((cat["base_name"], cat["attribute_name"]), ("MT-3016", "color"))
        self.assertEqual(cat["attribute_value"].lower(), "silver")
        self.assertTrue(cat["is_color"])

    def test_a_code_in_the_name_is_the_colour(self):
        cat = parse_label_name("1072/V-356")
        self.assertEqual((cat["base_name"], cat["attribute_name"], cat["attribute_value"]),
                         ("1072", "color", "V-356"))
        self.assertFalse(cat["is_color"])

    def test_a_code_after_the_sku_dot_is_the_colour(self):
        cat = derive_catalog("K48083İ.G93", "")
        self.assertEqual((cat["base_name"], cat["attribute_name"], cat["attribute_value"]),
                         ("K48083İ", "color", "G93"))

    def test_a_scanned_code_is_the_colour_too(self):
        cat = derive_catalog("MRK00047", "GREK", color="T08")
        self.assertEqual((cat["attribute_name"], cat["attribute_value"]), ("color", "T08"))

    def test_no_variant_part_means_no_attribute(self):
        for cat in (derive_catalog("K48083İ.", ""), parse_label_name("GREK")):
            self.assertIsNone(cat["attribute_name"])
            self.assertIsNone(cat["attribute_value"])
