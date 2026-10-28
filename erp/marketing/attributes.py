"""How variant attribute names and values are spelled.

One rule for every writer — the product page, the goods-receipt form, roll
scanning and imports. Before this each wrote its own way, which is how the
catalog came to hold `color`, `Color` and `colır`, and "130 x 210cm" beside
"130 x 210 cm" (see ~/Backups/erp/catalog-cleanup-log.md, C1 and C2).

The storefront (demfirat) reads these as stored: it keys labels and filters
on the attribute NAME (`color`, `header`, anything containing `size`) and
parses sizes as "W x H cm".

A value is written in words: lower case, a space inside one name, "+"
between the parts of a combination — "off white", "506 white+optic cord".
"_" belongs to SKUs, where it is what a "+" becomes (`SILVER_OFFWHITE`);
a value never holds one, so each character means one thing in each place.
"""
import re

_SIZE_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?$", re.I)
_BARE_NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")


def normalize_attribute_name(name):
    """Lower case, single spaces: "Size  Per Panel" → "size per panel"."""
    return " ".join(str(name or "").lower().split())


def is_size_attribute(name):
    return "size" in normalize_attribute_name(name)


def normalize_attribute_value(attribute_name, value):
    """The stored spelling of one value of `attribute_name`.

    Sizes read "130 x 210 cm"; everything else "dark cream", with "+"
    joining the parts of a combination and no spaces around it
    ("silver+off white"), whether it was typed "silver + Off_White" or
    not. Colours use American spelling ("gray"), which is what the
    storefront's colour map and Muhammed both prefer.
    """
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if is_size_attribute(attribute_name):
        m = _SIZE_RE.match(text)
        if m:
            return f"{m.group(1)} x {m.group(2)} cm"
        return text.lower()
    text = " ".join(text.lower().replace("_", " ").split())
    text = re.sub(r"\s*\+\s*", "+", text)
    if normalize_attribute_name(attribute_name) == "color":
        text = text.replace("grey", "gray")
    return text


# The languages a term can be worded in. English is the stored spelling; an
# English wording is only for a term that reads badly from its key
# ("750_matte_nacre" → "750 Matte Nacre").
CATALOG_LANGUAGES = ("en", "tr", "ru", "pl")

# What a wording is of: an attribute's own name, one of its values, or a
# product group's name.
WORDING_NAME, WORDING_VALUE, WORDING_GROUP = "name", "value", "group"

_WORDINGS_CACHE_KEY = "marketing.catalog_wordings"
_WORDINGS_CACHE_SECONDS = 60


def term_key(text):
    """How a term is matched: lower case, underscores as spaces, single
    spaces. "Sheet Type", "sheet_type" and "sheet  type" are one term —
    variant attributes spell theirs one way, product attributes another,
    and a wording is written once for both."""
    return " ".join(str(text or "").lower().replace("_", " ").split())


def _wordings():
    """{(kind, scope, key, language): text} — every wording there is. The
    table is small and read on every page that prints a variant, so it is
    held whole for a minute; saving a wording forgets it at once."""
    from django.core.cache import cache

    held = cache.get(_WORDINGS_CACHE_KEY)
    if held is None:
        from .models import CatalogWording
        held = {
            (kind, scope, key, language): text
            for kind, scope, key, language, text in CatalogWording.objects.values_list(
                "kind", "scope", "key", "language", "text")
        }
        cache.set(_WORDINGS_CACHE_KEY, held, _WORDINGS_CACHE_SECONDS)
    return held


def forget_wordings():
    from django.core.cache import cache
    cache.delete(_WORDINGS_CACHE_KEY)


def _reader_language(language=None):
    if language is None:
        from django.utils.translation import get_language
        language = get_language()
    return (language or "en").lower().split("-")[0]


def wording(attribute_name, value="", language=None):
    """What somebody wrote for this value — or, with no value, for the
    attribute's own name — in `language` (the reader's when not given).
    A value is looked for under its own attribute first, then among the
    wordings that hold for any attribute ("yes"). None when nobody has."""
    held, language = _wordings(), _reader_language(language)
    if not str(value or "").strip():
        return held.get((WORDING_NAME, "", term_key(attribute_name), language)) or None
    key = term_key(value)
    return (held.get((WORDING_VALUE, term_key(attribute_name), key, language))
            or held.get((WORDING_VALUE, "", key, language)) or None)


def group_label(name, language=None):
    """A product group's name for the reader, else as stored."""
    worded = _wordings().get((WORDING_GROUP, "", term_key(name), _reader_language(language)))
    return worded or str(name or "")


def attribute_label(name, language=None):
    """How a stored attribute name is shown: "size per panel" → "Size per
    panel", or its wording in the reader's language."""
    name = normalize_attribute_name(name)
    return wording(name, "", language) or (name[:1].upper() + name[1:])


def value_label(value):
    """How a stored value is shown: "dark cream" → "Dark cream",
    "gold+ecru" → "Gold + ecru". Still reads an older "dark_cream"."""
    text = re.sub(r"\s*\+\s*", " + ", str(value or "").replace("_", " "))
    return text[:1].upper() + text[1:]


def is_width_attribute(name):
    return normalize_attribute_name(name) == "width"


def display_value(attribute_name, value, language=None):
    """How one value of `attribute_name` reads on screen.

    A value somebody has worded in the reader's language reads that way
    ("750_matte_nacre" → "750 MAT SEDEF" in Turkish). The rest is for a
    value nobody has.

    The underscores are a storage habit, not something to read: a value
    is stored "cactus_green" and shown "Cactus green". A width is stored
    as the bare number the fabric is measured by ("250"), which in a
    column of variant values is a number with nothing to say what it
    measures — so it prints with its unit, "250 cm", the way a size
    already prints "160 x 200 cm". A width that was typed with a unit
    already ("150cm") is left as the person wrote it.
    """
    worded = wording(attribute_name, value, language)
    if worded:
        return worded
    text = value_label(value)
    if is_width_attribute(attribute_name) and _BARE_NUMBER_RE.match(text):
        return f"{text} cm"
    return text
