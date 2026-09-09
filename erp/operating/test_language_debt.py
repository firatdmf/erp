"""Two ways of writing a string that the catalogue cannot reach.

    {% if LANGUAGE_CODE|slice:":2" == "tr" %}Kaydet{% else %}Save{% endif %}

picks between two strings hardcoded in the template. It renders the right
words today, which is why it spread — order_detail.html alone had 41 of
them. What it costs: neither string is in the .po, so nothing can find,
change or reuse them; `makemessages` reports the page as fully
translated; and a third language means editing every branch by hand.

    {% trans "Kaydet" %}

is worse, because it looks right. The catalogue is keyed by English, so a
Turkish msgid has no entry, gettext hands the msgid straight back, and an
English page says "Kaydet".

order_detail.html is clear of both. The rest of the project is not, so
the counts below are ceilings rather than assertions of zero — they can
only come down, and a new one cannot be added quietly.

Run with:
    python manage.py test operating.test_language_debt
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

TURKISH_LETTERS = set("ğıİşçöüĞŞÇÖÜ")
BRANCH = re.compile(r"LANGUAGE_CODE\|slice")
ORDER_DETAIL = "operating/templates/operating/order_detail.html"

# What stood on the day this was written. Lower them as files are cleared;
# never raise them.
BRANCH_CEILING = 86
TURKISH_MSGID_CEILING = 22


def templates():
    for path in sorted(Path(".").rglob("*.html")):
        if "node_modules" in str(path):
            continue
        yield path, path.read_text(encoding="utf-8", errors="replace")


def msgids(src):
    return [m.group(2) for m in
            re.finditer(r"\{%\s*trans\s+(['\"])(.+?)\1\s*%\}", src)]


class TheOrderDetailPageIsClear(SimpleTestCase):
    """It was the worst of them: 41 branches, and two Turkish msgids the
    branch sweep would not have caught."""

    def setUp(self):
        self.src = Path(ORDER_DETAIL).read_text(encoding="utf-8")

    def test_it_picks_no_language_by_hand(self):
        found = BRANCH.findall(self.src)
        self.assertEqual(
            found, [],
            f"{len(found)} LANGUAGE_CODE branches are back on the order "
            f"detail page; write the English and let gettext do the rest.")

    def test_none_of_its_strings_are_written_in_turkish(self):
        turkish = sorted({m for m in msgids(self.src)
                          if any(c in TURKISH_LETTERS for c in m)})
        self.assertEqual(
            turkish, [],
            f"Turkish msgids have no catalogue entry and render as Turkish "
            f"on an English page: {turkish}")

    def test_the_count_it_shows_is_not_glued_together(self):
        """"This line has N scanned tops" — N sits mid-sentence, and in
        Turkish it lands somewhere else, so the sentence cannot be built
        by concatenation around the number."""
        self.assertIn("%(n)s scanned tops", self.src)
        self.assertIn(".replace('%(n)s', scannedCount)", self.src)


class TheRestIsCappedDebt(SimpleTestCase):
    def test_no_new_language_branches(self):
        total = sum(len(BRANCH.findall(src)) for _, src in templates())
        by_file = {str(p): len(BRANCH.findall(s))
                   for p, s in templates() if BRANCH.search(s)}
        self.assertLessEqual(
            total, BRANCH_CEILING,
            f"{total} LANGUAGE_CODE branches, up from {BRANCH_CEILING}:\n" +
            "\n".join(f"  {n:3}  {f}" for f, n in
                      sorted(by_file.items(), key=lambda x: -x[1])))

    def test_no_new_turkish_msgids(self):
        turkish = {m for _, src in templates() for m in msgids(src)
                   if any(c in TURKISH_LETTERS for c in m)}
        self.assertLessEqual(
            len(turkish), TURKISH_MSGID_CEILING,
            f"{len(turkish)} Turkish msgids, up from "
            f"{TURKISH_MSGID_CEILING}:\n" +
            "\n".join(f"  {t!r}" for t in sorted(turkish)))
