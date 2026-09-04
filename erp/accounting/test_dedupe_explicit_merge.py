"""Some duplicates the detection rules cannot see.

The legacy Laleli ledger kept one customer as three accounts, one per year
— "ÖZCAN ŞAHSİ 2024/2025/2026", each behind its own CRM contact. Every rule
the command has misses that group: the names differ by exactly the thing
that makes them separate rows, and there is no shared tax number or link to
catch them by. So the operator names the group, and the merge, the blockers
and the dry run stay the same.

Run with:
    python manage.py test accounting.test_dedupe_explicit_merge
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement
from crm.models import Contact


class ExplicitMerge(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Ergene Fabric")
        self.accounts = {}
        for code, year, amount in (("88888", "2024", "63836.66"),
                                   ("2025X", "2025", "37926.68"),
                                   ("99999", "2026", "29979.00")):
            cari = CariAccount.objects.create(
                book=self.book, code=code, name=f"ÖZCAN ŞAHSİ {year}",
                default_currency=self.usd,
                contact=Contact.objects.create(name=f"ÖZCAN ŞAHSİ {year}"))
            CariMovement.objects.create(
                cari=cari, book=self.book, date="2026-07-16",
                amount=Decimal(amount), currency=self.usd,
                movement_type="opening", description="Carried forward")
            cari.recompute_balance()
            self.accounts[code] = cari

    def _run(self, **kwargs):
        out = StringIO()
        call_command("dedupe_cari_accounts", stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def test_the_named_group_merges_into_the_named_survivor(self):
        self._run(book=self.book.pk, merge="88888,2025X", into="99999",
                  merge_cross_entity=True, apply=True)
        self.assertFalse(CariAccount.objects.filter(code__in=["88888", "2025X"]).exists())
        survivor = CariAccount.objects.get(code="99999")
        # Every movement moved, and the balance is the three added up.
        self.assertEqual(survivor.movements.count(), 3)
        self.assertEqual(survivor.recompute_balance(), Decimal("131742.34"))

    def test_the_survivor_is_the_one_named_not_the_one_ranked(self):
        """The ranking would keep whichever row has the most movements. When
        a human names the group a human names the keeper — three plausible
        rows is exactly when a guess is worth least."""
        self._run(book=self.book.pk, merge="99999,2025X", into="88888",
                  merge_cross_entity=True, apply=True)
        self.assertTrue(CariAccount.objects.filter(code="88888").exists())
        self.assertFalse(CariAccount.objects.filter(code="99999").exists())

    def test_a_dry_run_changes_nothing(self):
        out = self._run(book=self.book.pk, merge="88888,2025X", into="99999",
                        merge_cross_entity=True)
        self.assertIn("Dry run", out)
        self.assertEqual(CariAccount.objects.filter(book=self.book).count(), 3)

    def test_opening_balances_are_carried_not_dropped(self):
        for code, amount in (("88888", "63836.66"), ("2025X", "37926.68"),
                             ("99999", "29979.00")):
            CariAccount.objects.filter(code=code).update(opening_balance=Decimal(amount))
        self._run(book=self.book.pk, merge="88888,2025X", into="99999",
                  merge_cross_entity=True, apply=True)
        self.assertEqual(CariAccount.objects.get(code="99999").opening_balance,
                         Decimal("131742.34"))

    def test_cross_entity_still_needs_saying_out_loud(self):
        """Three different contacts is the blocker doing its job — after the
        merge the losing contacts have no account, and the next
        get_or_create_cari_for_contact would mint them fresh ones."""
        out = self._run(book=self.book.pk, merge="88888,2025X", into="99999",
                        apply=True)
        self.assertIn("different CRM entities", out)
        self.assertEqual(CariAccount.objects.filter(book=self.book).count(), 3)

    def test_an_unknown_code_is_an_error_not_a_silent_skip(self):
        with self.assertRaises(CommandError):
            self._run(book=self.book.pk, merge="NOPE", into="99999")

    def test_merging_across_books_is_refused(self):
        """A book is a separate business; merging across one would move
        money between them."""
        CariAccount.objects.create(book=self.other_book, code="E-1",
                                   name="ÖZCAN ŞAHSİ", default_currency=self.usd)
        with self.assertRaises(CommandError):
            self._run(merge="E-1", into="99999", merge_cross_entity=True)

    def test_an_ambiguous_code_asks_which_book(self):
        CariAccount.objects.create(book=self.other_book, code="99999",
                                   name="Someone else", default_currency=self.usd)
        with self.assertRaises(CommandError):
            self._run(merge="88888", into="99999", merge_cross_entity=True)

    def test_a_currency_mismatch_still_blocks(self):
        CariAccount.objects.filter(code="88888").update(default_currency=self.eur)
        out = self._run(book=self.book.pk, merge="88888", into="99999",
                        merge_cross_entity=True, apply=True)
        self.assertIn("different currencies", out)
        self.assertEqual(CariAccount.objects.filter(book=self.book).count(), 3)

    def test_merge_and_into_are_used_together(self):
        with self.assertRaises(CommandError):
            self._run(book=self.book.pk, merge="88888")
