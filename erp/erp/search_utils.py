"""Diacritic-insensitive search helpers.

Postgres `unaccent()` folds the *column* side of a comparison — ş→s,
ö→o, ç→c, ğ→g, ü→u, ı→i, İ→I — and Django exposes it as the
`__unaccent` lookup. It leaves the *search term* alone, though, so a
user typing "şişe" would still miss a row stored as "Sise". Folding
both sides is what makes the match symmetric, and `fold_search_term`
is the Python half of that pair.

Use `unaccent_icontains` for text columns. It is not valid on
ArrayField columns (email/phone on Contact and Company) — those hold
no diacritics anyway, so leave them on plain `icontains`.
"""
import unicodedata

from django.db.models import Q

# NFKD decomposes ş, ö, ç, ğ and ü into a base letter plus a combining
# mark we can drop, but the Turkish dotless ı and dotted İ are letters
# in their own right with no decomposition — they need naming. The rest
# are listed too so the mapping reads as the full Turkish set.
_TR_FOLD = str.maketrans({
    'ı': 'i', 'İ': 'I',
    'ş': 's', 'Ş': 'S',
    'ğ': 'g', 'Ğ': 'G',
    'ç': 'c', 'Ç': 'C',
    'ö': 'o', 'Ö': 'O',
    'ü': 'u', 'Ü': 'U',
})


def fold_search_term(term):
    """Strip diacritics from a search term the way Postgres `unaccent()`
    strips them from the column it is compared against."""
    text = unicodedata.normalize('NFKD', (term or '').translate(_TR_FOLD))
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def unaccent_icontains(term, *fields):
    """A Q matching `term` in any of `fields`, ignoring diacritics on
    both sides — so "sise" finds "Şişe" and "ŞİŞE" finds "sise".

        qs.filter(unaccent_icontains(q, 'name', 'company__name'))

    An empty term yields an empty Q, which filters nothing out.
    """
    folded = fold_search_term(term).strip()
    if not folded:
        return Q()
    q = Q()
    for field in fields:
        q |= Q(**{f'{field}__unaccent__icontains': folded})
    return q
