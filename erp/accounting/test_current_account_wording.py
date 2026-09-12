"""The account is called a current account, in English, everywhere.

9940e746 renamed the model, the fields and the comments, but a rename
sweeps identifiers and leaves everything shaped otherwise: the old
Turkish word went on sitting in English sentences, in CSS class names,
in HTML name attributes and in template variables. Several of those were
not cosmetic. The CRM sidebars posted the old checkbox name, so no record
created there got an account; the statement heading read an old variable
and printed no name; the payment list's account search sent a parameter
the view no longer read.

So the source does not carry the word at all — not in code, comments,
docs, class names or test fixtures. Three places are exempt, because
changing them would be wrong rather than tidy:

* migrations, whose filenames are recorded in django_migrations and whose
  operations have to keep describing the schema as it stood;
* the Turkish catalogue (locale/), where it is the right Turkish word;
* the database, where Laleli's accounts keep the codes they were issued.

Run with:
    python manage.py test accounting.test_current_account_wording
"""
import os
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

# The letters Turkish has and English does not.
TURKISH_LETTERS = set("ğıİşçöüĞŞÇÖÜ")

# The bracket keeps this file from matching its own pattern. Lower case
# only counts at the start of a word, so an English word that merely
# contains those letters is not a hit; a capital counts anywhere, which
# catches camelCase and upper-case codes.
OLD_TERM = re.compile(r"(?<![A-Za-z])c[a]ri|C[a]ri|C[A]RI")

SKIP_DIRS = {"migrations", "locale", "media", "staticfiles", "node_modules",
             "__pycache__", ".git"}
TEXT_SUFFIXES = {".py", ".html", ".js", ".css", ".md", ".json", ".txt",
                 ".toml", ".yml", ".yaml", ".sh"}


def source_files():
    for dirpath, dirnames, filenames in os.walk(settings.BASE_DIR):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if Path(name).suffix in TEXT_SUFFIXES:
                yield Path(dirpath, name)


def template_msgids():
    """Every {% trans %} msgid in the project, with where it came from."""
    for path in sorted(Path(".").rglob("*.html")):
        if "node_modules" in str(path):
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\{%\s*trans\s+(['\"])(.+?)\1\s*%\}", src):
            yield str(path), m.group(2)


class TheOldTermIsGone(SimpleTestCase):
    def test_no_source_file_uses_it(self):
        root = Path(settings.BASE_DIR)
        offenders = []
        for path in source_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if OLD_TERM.search(line):
                    offenders.append(f"  {path.relative_to(root)}:{n}: {line.strip()[:100]}")
        self.assertEqual(
            offenders, [],
            "the old Turkish term is back — say current account:\n" +
            "\n".join(offenders))

    def test_the_example_code_matches_what_a_new_book_mints(self):
        """The help text quotes an example code. It has to be the one a
        book created today would actually get, or it teaches a format
        nothing uses — which is exactly what the old example had become."""
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
