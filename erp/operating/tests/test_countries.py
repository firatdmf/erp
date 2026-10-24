# to run this test, use the command:
# python manage.py test operating.tests.test_countries

"""Web addresses hold ISO codes; people read names, in their language.

See operating/countries.py.
"""
from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import translation

from operating.countries import country_choices, country_name


class CountryNameTest(SimpleTestCase):
    def test_a_code_reads_as_its_name_in_the_readers_language(self):
        with translation.override("en"):
            self.assertEqual(country_name("DE"), "Germany")
            self.assertEqual(country_name("tr"), "Türkiye")
        with translation.override("tr"):
            self.assertEqual(country_name("DE"), "Almanya")

    def test_a_name_typed_before_codes_is_shown_as_it_is(self):
        for value in ("Turkey", "Türkiye", "XX", ""):
            with self.subTest(value=value):
                self.assertEqual(country_name(value), value)

    def test_the_list_holds_every_country_once_by_name(self):
        with translation.override("en"):
            choices = country_choices()
        codes = [code for code, _ in choices]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertIn(("PL", "Poland"), choices)
        names = [name.casefold() for _, name in choices]
        self.assertEqual(names, sorted(names))

    def test_the_filter(self):
        with translation.override("en"):
            out = Template("{% load operating_tags %}{{ c|country_name }}").render(Context({"c": "KZ"}))
        self.assertEqual(out, "Kazakhstan")
