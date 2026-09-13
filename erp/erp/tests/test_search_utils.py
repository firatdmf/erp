from django.test import TestCase

from crm.models import Company
from erp.search_utils import fold_search_term, unaccent_icontains


class FoldSearchTermTests(TestCase):
    """The Python half has to fold exactly what Postgres `unaccent()`
    folds, or the two sides of the comparison drift apart."""

    def test_folds_turkish_letters(self):
        self.assertEqual(fold_search_term('Şişe Cam'), 'Sise Cam')
        self.assertEqual(fold_search_term('çöğüş'), 'cogus')

    def test_folds_both_dotted_and_dotless_i(self):
        # ı and İ have no Unicode decomposition, so they are the two
        # that a plain NFKD strip would miss.
        self.assertEqual(fold_search_term('ışık'), 'isik')
        self.assertEqual(fold_search_term('İstanbul'), 'Istanbul')

    def test_leaves_plain_text_alone(self):
        self.assertEqual(fold_search_term('Order 1234'), 'Order 1234')
        self.assertEqual(fold_search_term(''), '')
        self.assertEqual(fold_search_term(None), '')


class UnaccentIcontainsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.turkish = Company.objects.create(name='Şişe Cam Ambalaj')
        cls.plain = Company.objects.create(name='Sise Plastik')

    def _search(self, term):
        return set(
            Company.objects
            .filter(unaccent_icontains(term, 'name'))
            .values_list('name', flat=True)
        )

    def test_plain_letters_find_accented_rows(self):
        self.assertEqual(
            self._search('sise'),
            {'Şişe Cam Ambalaj', 'Sise Plastik'},
        )

    def test_accented_letters_find_plain_rows(self):
        self.assertEqual(
            self._search('şişe'),
            {'Şişe Cam Ambalaj', 'Sise Plastik'},
        )

    def test_dotless_i_matches_dotted_i(self):
        self.assertIn('Şişe Cam Ambalaj', self._search('ŞIŞE CAM'))

    def test_still_narrows(self):
        self.assertEqual(self._search('ambalaj'), {'Şişe Cam Ambalaj'})

    def test_empty_term_filters_nothing_out(self):
        self.assertEqual(len(self._search('')), 2)
