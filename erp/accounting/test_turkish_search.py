"""Finding an account by typing its name.

Two separate things break Turkish search, and both did.

SQL's ILIKE folds only ASCII case, so 'ı'/'I' and 'i'/'İ' never meet, and
a reader on a keyboard without Turkish letters cannot produce the Ü in
GÜRHAN at all. Both sides are folded to plain uppercase ASCII instead.

And text read from a macOS filename arrives DECOMPOSED — a dotted İ as I
plus a combining dot. Stored that way it looks identical everywhere and is
invisible in a diff, but the browser sends the composed form and Postgres
compares bytes, so the row cannot be found at all. The importer composes
at its boundary; this pins that it keeps doing so.
"""
import unicodedata

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from accounting.views_accounts import tr_fold


class TurkishFold(TestCase):
    def test_it_folds_to_ascii_uppercase(self):
        self.assertEqual(tr_fold("Gülşen"), "GULSEN")
        self.assertEqual(tr_fold("ÇİFTÇİOĞLU"), "CIFTCIOGLU")
        self.assertEqual(tr_fold("ışıl"), "ISIL")
        self.assertEqual(tr_fold("İREM"), "IREM")

    def test_the_dotted_and_dotless_i_both_land_on_ascii_i(self):
        """The pair ILIKE cannot fold, and the reason this exists."""
        self.assertEqual(tr_fold("İREM"), tr_fold("irem"))
        self.assertEqual(tr_fold("IŞIL"), tr_fold("ışıl"))


class SearchingTheAccountList(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric")
        self.user = get_user_model().objects.create_user(username="searcher", password="pw")
        self.user.member.books.set([self.book])
        self.client.force_login(self.user)
        for code, name in (("ACC-001", "GÜLŞEN TEKSTİL"), ("ACC-002", "ÇİFTÇİOĞLU"),
                           ("ACC-003", "IŞIL DOĞAN"), ("ACC-004", "İREM")):
            CariAccount.objects.create(book=self.book, code=code, name=name,
                                       default_currency=self.usd)

    def found(self, q):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.book.pk}),
                            {"q": q})
        self.assertEqual(r.status_code, 200)
        return {c.code for c in r.context["caris"]}

    def test_typing_the_turkish_spelling_finds_it(self):
        self.assertEqual(self.found("GÜLŞEN"), {"ACC-001"})
        self.assertEqual(self.found("gülşen"), {"ACC-001"})

    def test_typing_plain_ascii_finds_it_too(self):
        """The reader may not have a Turkish keyboard, and requiring one
        to look anything up is a quiz, not a search box."""
        self.assertEqual(self.found("gulsen"), {"ACC-001"})
        self.assertEqual(self.found("CIFTCIOGLU"), {"ACC-002"})
        self.assertEqual(self.found("isil dogan"), {"ACC-003"})

    def test_both_spellings_of_i_find_the_same_row(self):
        self.assertEqual(self.found("irem"), {"ACC-004"})
        self.assertEqual(self.found("IREM"), {"ACC-004"})
        self.assertEqual(self.found("İREM"), {"ACC-004"})

    def test_a_name_stored_decomposed_is_still_unreachable(self):
        """Folding does not rescue NFD — translate() cannot see a
        combining mark as part of the letter before it. This is why the
        importer composes on the way in rather than relying on search."""
        CariAccount.objects.create(
            book=self.book, code="ACC-009",
            name=unicodedata.normalize("NFD", "ZÜMRÜT AKÇA"),
            default_currency=self.usd)
        self.assertEqual(self.found("zumrut"), set())

    def test_the_search_still_narrows(self):
        self.assertEqual(self.found("tekstil"), {"ACC-001"})
        self.assertEqual(self.found("nothing here"), set())


class ImporterComposesWhatItReads(TestCase):
    def test_names_from_the_map_are_composed(self):
        """macOS filenames are NFD; anything written from one has to be
        composed first or the row is unsearchable the moment it lands."""
        from accounting.management.commands.import_ergene_balances import nfc
        decomposed = unicodedata.normalize("NFD", "İREM")
        self.assertNotEqual(decomposed, "İREM")
        self.assertEqual(nfc(decomposed), "İREM")
        self.assertEqual(unicodedata.normalize("NFC", nfc(decomposed)), nfc(decomposed))
