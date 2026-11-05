"""A downloaded document's file name starts with who it is for."""
from django.test import SimpleTestCase

from erp.download_names import client_filename, disposition


class ClientFilename(SimpleTestCase):
    def test_the_client_comes_first(self):
        self.assertEqual(client_filename("Zümrüt", "statement_ACC-060.pdf"),
                         "Zümrüt - statement_ACC-060.pdf")

    def test_no_client_leaves_the_name_alone(self):
        self.assertEqual(client_filename("", "order_ORD-1.pdf"), "order_ORD-1.pdf")
        self.assertEqual(client_filename(None, "order_ORD-1.pdf"), "order_ORD-1.pdf")

    def test_characters_a_file_system_refuses_are_dropped(self):
        self.assertEqual(client_filename('A/B: "Textile"\n', "x.pdf"),
                         "A B Textile - x.pdf")

    def test_a_long_name_is_cut(self):
        name = client_filename("N" * 200, "x.pdf")
        self.assertEqual(name, "N" * 60 + " - x.pdf")


class Disposition(SimpleTestCase):
    def test_turkish_letters_travel_as_utf8(self):
        value = disposition("Şahin - order_ORD-1.pdf", attachment=True)
        self.assertTrue(value.startswith("attachment; filename*=utf-8''"))
        self.assertIn("%C5%9Eahin", value)

    def test_ascii_stays_plain_and_inline_by_default(self):
        self.assertEqual(disposition("Ada - x.pdf"), 'inline; filename="Ada - x.pdf"')
