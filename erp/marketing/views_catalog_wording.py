"""How catalog terms read in each language.

A term — an attribute's name, one of its values, a product group's name —
is stored once, as an English key ("dark_cream"). Its wordings used to
live in the storefront's code (a table in demfirat's translate.ts), so the
ERP printed the key to everybody and a new value needed a storefront
release to be read in Turkish. They are kept here now: one page to write
them, the ERP reading them for whoever is looking, and one endpoint the
storefront asks.
"""
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _gettext
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .attributes import (CATALOG_LANGUAGES, WORDING_GROUP, WORDING_NAME,
                         WORDING_VALUE, term_key)
from .models import (CatalogWording, ProductAttribute, ProductCategory,
                     ProductVariantAttribute, ProductVariantAttributeValue)

# The page's sections that are not one attribute's values.
NAMES, GROUPS, ANY = "names", "groups", "any"


def _attribute_names():
    """Every attribute there is, as terms: the ones variants carry and the
    ones written on products, which spell the same name differently."""
    names = {term_key(n) for n in ProductVariantAttribute.objects.values_list("name", flat=True)}
    names |= {term_key(n) for n in ProductAttribute.objects.values_list("name", flat=True).distinct()}
    names |= set(CatalogWording.objects.filter(kind=WORDING_NAME).values_list("key", flat=True))
    names |= set(CatalogWording.objects.filter(kind=WORDING_VALUE).exclude(scope="")
                 .values_list("scope", flat=True))
    return sorted(n for n in names if n)


def _section(section):
    """(kind, scope) of the wordings a section of the page edits."""
    if section == NAMES:
        return WORDING_NAME, ""
    if section == GROUPS:
        return WORDING_GROUP, ""
    if section == ANY:
        return WORDING_VALUE, ""
    return WORDING_VALUE, section


def _carried(section):
    """{term: how many products or variants carry it} for a section."""
    carried = Counter()
    if section == NAMES:
        for name in _attribute_names():
            carried[name] += 0
    elif section == GROUPS:
        for name, n in ProductCategory.objects.annotate(n=Count("product")).values_list("name", "n"):
            if name:
                carried[term_key(name)] += n
    elif section != ANY:
        for name, value, n in (ProductVariantAttributeValue.objects.annotate(n=Count("variants"))
                               .values_list("product_variant_attribute__name",
                                            "product_variant_attribute_value", "n")):
            if term_key(name) == section:
                carried[term_key(value)] += n
        for name, value in ProductAttribute.objects.values_list("name", "value"):
            if term_key(name) == section and term_key(value):
                carried[term_key(value)] += 1
    return carried


def _rows(section):
    kind, scope = _section(section)
    worded = {}
    for key, language, text in CatalogWording.objects.filter(kind=kind, scope=scope).values_list(
            "key", "language", "text"):
        worded.setdefault(key, {})[language] = text
    carried = _carried(section)
    rows = []
    for key in sorted(set(carried) | set(worded)):
        texts = worded.get(key, {})
        rows.append({
            "key": key,
            "carried": carried.get(key, 0) if section not in (NAMES, ANY) else None,
            "texts": [(language, texts.get(language, "")) for language in CATALOG_LANGUAGES],
        })
    return rows


def _save(kind, scope, key, texts):
    """Write one term's wordings; an emptied language is taken away.
    Returns how many wordings changed."""
    key = term_key(key)
    if not key:
        return 0
    changed = 0
    for language in CATALOG_LANGUAGES:
        text = (texts.get(language) or "").strip()
        held = CatalogWording.objects.filter(
            kind=kind, scope=scope, key=key, language=language).first()
        if text and held is None:
            CatalogWording.objects.create(
                kind=kind, scope=scope, key=key, language=language, text=text)
            changed += 1
        elif text and held.text != text:
            held.text = text
            held.save()
            changed += 1
        elif not text and held is not None:
            held.delete()
            changed += 1
    return changed


@login_required
def catalog_wording(request):
    attributes = _attribute_names()
    section = term_key(request.POST.get("section") or request.GET.get("section") or NAMES)
    if section not in (NAMES, GROUPS, ANY) and section not in attributes:
        section = NAMES

    if request.method == "POST":
        kind, scope = _section(section)
        changed = 0
        with transaction.atomic():
            for index in range(int(request.POST.get("rows") or 0)):
                changed += _save(kind, scope, request.POST.get(f"key_{index}", ""), {
                    language: request.POST.get(f"text_{index}_{language}")
                    for language in CATALOG_LANGUAGES})
            # One more term, typed in the page's last row.
            changed += _save(kind, scope, request.POST.get("new_key", ""), {
                language: request.POST.get(f"new_text_{language}")
                for language in CATALOG_LANGUAGES})
        messages.success(request, _gettext("%(count)s wordings saved.") % {"count": changed})
        return redirect(f"{reverse('marketing:catalog_wording')}?section={section}")

    return render(request, "marketing/catalog_wording.html", {
        "attributes": attributes,
        "section": section,
        "is_attribute": section not in (NAMES, GROUPS, ANY),
        "rows": _rows(section),
        "languages": CATALOG_LANGUAGES,
    })


@require_GET
@cache_control(public=True, max_age=300)
def catalog_wording_api(request):
    """Every wording, for the storefront:
    {"names":  {"color": {"tr": "Renk"}},
     "values": {"color": {"white": {"tr": "Beyaz"}}, "": {"yes": {"tr": "Evet"}}},
     "groups": {"ready-made curtain": {"tr": "Hazır Perde"}}}
    Terms are spelled as attributes.term_key spells them: lower case, spaces
    for underscores. "" holds the values worded for any attribute."""
    names, values, groups = {}, {}, {}
    for kind, scope, key, language, text in CatalogWording.objects.values_list(
            "kind", "scope", "key", "language", "text"):
        if kind == WORDING_NAME:
            names.setdefault(key, {})[language] = text
        elif kind == WORDING_GROUP:
            groups.setdefault(key, {})[language] = text
        else:
            values.setdefault(scope, {}).setdefault(key, {})[language] = text
    return JsonResponse({"names": names, "values": values, "groups": groups})
