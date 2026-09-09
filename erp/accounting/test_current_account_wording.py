"""The account is called a current account, in English, everywhere.

9940e746 renamed the model, the fields and the comments, but a rename
sweeps identifiers and leaves prose: "cari" went on sitting inside
English sentences that a reader who asked for English still saw —
"reverses the cari debt", "sync the cari ledger", "(cari accounts)".
Two whole sentences in invoice_detail.html were Turkish msgids, which
the catalogue cannot reach at all, so English readers got Turkish and
Turkish readers got the same string by accident.

The one exception is CARI-001. That is not the word — it is the account
CODE, auto-assigned by signals_accounts and carried by live accounts, so
help text naming it is documentation of real data. Renaming the prefix
would be a data migration, not a wording fix.

Run with:
    python manage.py test accounting.test_current_account_wording
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

# The letters Turkish has and English does not.
TURKISH_LETTERS = set("ğıİşçöüĞŞÇÖÜ")
# CARI-001 and friends: the code, not the word.
ACCOUNT_CODE = re.compile(r"CARI-\d|CARI-XXX|CARI-nnn")


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
            if re.search(r"\bcari\b", text, re.I) and not ACCOUNT_CODE.search(text)
        })
        self.assertEqual(
            offenders, [],
            "these strings still say 'cari' in English prose:\n" +
            "\n".join(f"  {p}: {t!r}" for p, t in offenders))

    def test_the_account_code_is_left_alone(self):
        """Guards the exception, so a future sweep does not "fix" the help
        text into describing a prefix that no account actually has."""
        codes = [t for _, t in template_msgids() if ACCOUNT_CODE.search(t)]
        self.assertTrue(
            codes, "the CARI-001 account-code help text has gone missing")


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
