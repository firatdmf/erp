"""Every test starts in the site's language (erp.test_runner).

A request in Turkish leaves Turkish switched on behind it, so without the
runner's reset the second test here would read Turkish. Django runs one
class's tests in one worker, in name order, so the first always runs
before the second.
"""
from django.conf import settings
from django.test import SimpleTestCase
from django.utils import translation


class EachTestStartsInTheSiteLanguageTest(SimpleTestCase):

    def test_1_a_page_asked_for_in_turkish(self):
        self.client.get("/", HTTP_ACCEPT_LANGUAGE="tr")
        self.assertEqual(translation.get_language(), "tr")

    def test_2_the_next_test_is_back_in_english(self):
        self.assertEqual(translation.get_language(), settings.LANGUAGE_CODE)
