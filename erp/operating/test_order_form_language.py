"""English is the source language of the order form.

The form had grown three ways of saying something in Turkish, and all
three put Turkish on the screen for a reader who had asked for English:

  * `{% trans "Ekle" %}` — a Turkish msgid. It looks translated and can
    never be: the catalogue is keyed by English, so this string has no
    entry, gettext hands back the msgid, and the English page says
    "Ekle".
  * `showToast('Barkod bulunamadı')` — a bare literal, wrapped in
    nothing, invisible to the catalogue in either direction.
  * `{% if LANGUAGE_CODE|slice:":2" == "tr" %}…{% else %}…{% endif %}` —
    a hand-rolled two-language switch that keeps the translations out of
    the .po where nobody can find or reuse them.

All three are now English msgids with their Turkish in
locale/tr/LC_MESSAGES/django.po. This test keeps them that way, because
the mistake is invisible in review: a Turkish msgid is perfectly valid
Django and only shows itself on a rendered English page.

Run with:
    python manage.py test operating.test_order_form_language
"""
import re

from django.test import SimpleTestCase
from django.utils import translation

FORM = "operating/templates/operating/partials/create_order_form.html"

# The letters that exist in Turkish and not in English. Enough to catch a
# Turkish string, though not every one — "opsiyonel" has none of them,
# which is why the reviewer's eye is not the thing being relied on here.
TURKISH_LETTERS = set("ğıİşçöüĞŞÇÖÜ")


def read_form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def msgids(src):
    return [m.group(2) for m in
            re.finditer(r"\{%\s*trans\s+(['\"])(.+?)\1\s*%\}", src)]


class TheFormSpeaksEnglish(SimpleTestCase):
    def test_no_msgid_is_written_in_turkish(self):
        turkish = sorted({m for m in msgids(read_form())
                          if any(c in TURKISH_LETTERS for c in m)})
        self.assertEqual(
            turkish, [],
            "these msgids are Turkish, so the catalogue has no entry for "
            "them and an English page renders the Turkish: " + repr(turkish))

    def test_no_string_is_shown_without_going_through_the_catalogue(self):
        """A bare literal in a toast is neither English nor translatable."""
        bare = []
        for m in re.finditer(r"showToast\(\s*(.+?),\s*'(?:error|warning|success)'",
                             read_form()):
            arg = m.group(1)
            if any(c in TURKISH_LETTERS for c in arg):
                bare.append(arg.strip()[:60])
        self.assertEqual(bare, [], "untranslatable Turkish in a toast: " + repr(bare))

    def test_the_language_is_not_chosen_by_hand(self):
        """`{% if LANGUAGE_CODE %}` picks between two hardcoded strings and
        hides both from the .po. gettext already does this job."""
        self.assertNotIn("LANGUAGE_CODE|slice", read_form())

    def test_every_string_the_form_shows_has_its_turkish(self):
        """The mirror of the complaint: an English msgid with no entry
        leaves a Turkish reader looking at English. Only checks the
        strings this pass introduced or touched — the rest is older debt,
        listed by test_untranslated_strings_are_known_debt below."""
        touched = [
            "Add", "Scan or type a barcode", "Scan or type a roll barcode",
            "Scan, type, or paste a list of barcodes", "Scan with the camera",
            "Enter customer details", "Purchase cost", "Cut part of it",
            "click to pick", "This stock item belongs to another book",
            "add a separate line for that book", "A name is required",
            "Could not be created", "Barcode not found",
            "The product could not be added", "Barcode could not be verified",
            "This barcode has already been added", "The camera is not supported",
            "Retail Sale", "Retail Sale (Walk-in)", "optional",
            "Pick a customer before saving the order", "added", "skipped",
        ]
        with translation.override("tr"):
            missing = [s for s in touched if translation.gettext(s) == s]
        self.assertEqual(missing, [], "no Turkish for: " + repr(missing))

    def test_untranslated_strings_are_known_debt(self):
        """Strings that predate this pass and still have no Turkish. Not a
        failure — a ceiling, so the number cannot quietly grow."""
        with translation.override("tr"):
            missing = {m for m in msgids(read_form())
                       if translation.gettext(m) == m}
        # "SKU" is the same word in both languages and needs no entry.
        missing.discard("SKU")
        self.assertLessEqual(
            len(missing), 25,
            f"{len(missing)} strings on the order form have no Turkish: "
            f"{sorted(missing)}")
