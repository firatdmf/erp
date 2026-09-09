"""The account is called a current account, in English, everywhere.

9940e746 renamed the model, the fields and the comments, but a rename
sweeps identifiers and leaves prose: "cari" went on sitting inside
English sentences that a reader who asked for English still saw —
"reverses the cari debt", "sync the cari ledger", "(cari accounts)".
Two whole sentences in invoice_detail.html were Turkish msgids, which
the catalogue cannot reach at all, so English readers got Turkish and
Turkish readers got the same string by accident.

There is no exception for CARI-001 either. The code prefix is a per-book
setting that was moved to ACC — Ergene mints ACC-062 next, keeping its
five legacy CARI codes — and the model default now says ACC too, so a
new book starts there. Only Laleli is still set to CARI, which is a row
in its settings rather than anything in the source. Live accounts keep
the codes they were issued; that is data, and this test reads templates.

Run with:
    python manage.py test accounting.test_current_account_wording
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

# The letters Turkish has and English does not.
TURKISH_LETTERS = set("ğıİşçöüĞŞÇÖÜ")


def template_msgids():
    """Every {% trans %} msgid in the project, with where it came from."""
    for path in sorted(Path(".").rglob("*.html")):
        if "node_modules" in str(path):
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\{%\s*trans\s+(['\"])(.+?)\1\s*%\}", src):
            yield str(path), m.group(2)


class NobodySaysCariInEnglish(SimpleTestCase):
    def test_no_english_string_calls_it_a_cari(self):
        offenders = sorted({
            (path, text) for path, text in template_msgids()
            if re.search(r"\bcari\b", text, re.I)
        })
        self.assertEqual(
            offenders, [],
            "these strings still say 'cari' in English prose:\n" +
            "\n".join(f"  {p}: {t!r}" for p, t in offenders))

    def test_the_example_code_matches_what_a_new_book_mints(self):
        """The help text quotes an example code. It has to be the one a
        book created today would actually get, or it teaches a format
        nothing uses — which is exactly what CARI-001 had become."""
        from accounting.models_accounts import CurrentAccountSettings
        default = CurrentAccountSettings._meta.get_field(
            "current_account_code_prefix").default
        examples = [t for _, t in template_msgids() if re.search(r"[A-Z]+-00\d", t)]
        self.assertTrue(examples, "the example account code has gone missing")
        for text in examples:
            for code in re.findall(r"([A-Z]+)-00\d", text):
                self.assertEqual(
                    code, default,
                    f"help text shows {code}-001 but a new book mints "
                    f"{default}-001: {text!r}")


class TurkishMsgidsAreCappedDebt(SimpleTestCase):
    """A Turkish msgid can never be translated — the catalogue is keyed by
    English — so it renders as Turkish no matter which language was asked
    for. 24 remain across the project, all predating this. Not a failure;
    a ceiling, so the number can only come down."""

    def test_the_count_does_not_grow(self):
        turkish = {t for _, t in template_msgids()
                   if any(c in TURKISH_LETTERS for c in t)}
        self.assertLessEqual(
            len(turkish), 24,
            f"{len(turkish)} Turkish msgids, up from 24. New ones cannot be "
            f"translated and will show Turkish on an English page:\n" +
            "\n".join(f"  {t!r}" for t in sorted(turkish)))
