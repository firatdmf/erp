"""Bridge warehouse roll scans into the marketing catalog.

A scanned fabric roll is really a *variant*: it carries the stock (meters),
an MRK SKU and a barcode. Its base name (e.g. "MT-3016") is the *main
product* that groups all of its colour/model variants. This module:

  1. Parses a scanned product name into (base_name, attribute, value).
  2. Idempotently creates/links a HIDDEN marketing Product (main) + a
     ProductVariant (the scanned item) so the catalog mirrors the warehouse
     without ever exposing these to the website (featured=False).

Design notes:
  - marketing.ProductVariantAttribute.save() lower-cases + strips spaces;
    ProductVariantAttributeValue.save() lower-cases + turns spaces into "_".
    get_or_create() does its DB lookup with the RAW arg before save() runs,
    so we must pre-normalize the lookup keys ourselves or we'd miss existing
    rows and hit the unique_together constraint. _norm_attr / _norm_value
    below mirror those save() rules exactly.
  - variant_sku is GLOBALLY unique; the same MRK code must map to exactly one
    variant. If it already points at a different base product we raise
    CatalogSyncConflict rather than silently re-parenting.
"""
from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum


class CatalogSyncConflict(Exception):
    """Raised when a variant_sku already belongs to a different base product."""


# ---------------------------------------------------------------------------
# Turkish → English colour dictionary.
# EDIT HERE: keys are the label tokens (any case), values the English colour
# stored on the catalog. A token NOT in this map is treated as a *model*
# attribute instead of a colour. This is the single place to curate colours.
# ---------------------------------------------------------------------------
TR_EN_COLORS = {
    "BEYAZ": "WHITE",
    "SIYAH": "BLACK",
    "GRI": "GREY",
    "GUMUS": "SILVER",
    "KREM": "CREAM",
    "EKRU": "ECRU",
    "BEJ": "BEIGE",
    "KAHVE": "BROWN",
    "KAHVERENGI": "BROWN",
    "VIZON": "MINK",
    "LACIVERT": "NAVY",
    "MAVI": "BLUE",
    "TURKUAZ": "TURQUOISE",
    "YESIL": "GREEN",
    "KIRMIZI": "RED",
    "BORDO": "BURGUNDY",
    "PEMBE": "PINK",
    "PUDRA": "POWDER",
    "MOR": "PURPLE",
    "LILA": "LILAC",
    "SARI": "YELLOW",
    "HARDAL": "MUSTARD",
    "TURUNCU": "ORANGE",
    "ALTIN": "GOLD",
    "BAKIR": "COPPER",
    "ANTRASIT": "ANTHRACITE",
    "FUME": "SMOKE",
    "TABA": "TAN",
}


def _fold(token: str) -> str:
    """Upper-case a token for colour-dictionary lookup, handling Turkish
    dotted/dotless i correctly (str.upper() alone mangles them) and
    stripping accents so 'GÜMÜŞ' matches the ASCII key 'GUMUS'."""
    if not token:
        return ""
    t = token.strip()
    # Turkish-aware upper: i→İ then upper; ı already upper-maps to I.
    t = t.replace("i", "İ").replace("ı", "I").upper()
    # Fold accented Turkish letters to ASCII so dictionary keys stay simple.
    table = str.maketrans({
        "İ": "I", "Ş": "S", "Ğ": "G", "Ü": "U", "Ö": "O", "Ç": "C", "Â": "A",
    })
    return t.translate(table)


def _norm_attr(name: str) -> str:
    """Mirror ProductVariantAttribute.save() normalization."""
    return (name or "").lower().replace(" ", "")


def _norm_value(value: str) -> str:
    """Mirror ProductVariantAttributeValue.save() normalization."""
    return (value or "").lower().replace(" ", "_")


# Modifiers that precede a colour, e.g. "AÇIK KREM" (light cream).
_COLOR_MODIFIERS = {"ACIK": "LIGHT", "KOYU": "DARK", "ORTA": "MEDIUM"}


def translate_color(token):
    """Return the English colour for a Turkish colour phrase, or None if it
    isn't a colour. Handles single words ("GÜMÜŞ"→"SILVER") and modifier +
    colour ("AÇIK KREM"→"LIGHT CREAM", "KOYU MAVİ"→"DARK BLUE")."""
    folded = _fold(token)
    if not folded:
        return None
    if folded in TR_EN_COLORS:
        return TR_EN_COLORS[folded]
    words = folded.split()
    if len(words) >= 2 and words[0] in _COLOR_MODIFIERS and words[-1] in TR_EN_COLORS:
        return _COLOR_MODIFIERS[words[0]] + " " + TR_EN_COLORS[words[-1]]
    if len(words) >= 2 and words[-1] in TR_EN_COLORS:
        return TR_EN_COLORS[words[-1]]
    return None


def parse_label_name(name: str) -> dict:
    """Split a scanned product NAME into base product + variant token.

    Precedence:
      1. If there's a SPACE → split on the FIRST space.
         "MT-3016 GÜMÜŞ" -> base="MT-3016", token="GÜMÜŞ"
      2. Else if there's a SPECIAL character (non-alphanumeric) → split on
         the FIRST one (the separator itself is dropped).
         "1072/V-356"   -> base="1072", token="V-356"

    The token decides the attribute:
      - token folds to a key in TR_EN_COLORS -> attribute "color",
        value = the English colour (upper-case for display).
      - otherwise                            -> attribute "model",
        value = the token as printed.
    No space and no special char -> base only, no variant.

    Returns: {base_name, attribute_name, attribute_value, original_token, is_color}
    """
    raw = (name or "").strip()
    if not raw:
        return {"base_name": "", "attribute_name": None, "attribute_value": None,
                "original_token": None, "is_color": False}

    if " " in raw:
        base, _, token = raw.partition(" ")
    else:
        # No space → split on the first non-alphanumeric character (treat
        # Turkish letters as alphanumeric so "GÜMÜŞ" stays whole).
        m = re.search(r"[^0-9A-Za-zğüşıöçĞÜŞİÖÇ]", raw)
        if m and m.start() > 0:
            base, token = raw[:m.start()], raw[m.start() + 1:]
        else:
            base, token = raw, ""
    base = base.strip()
    token = token.strip()

    if not token:
        return {"base_name": base, "attribute_name": None, "attribute_value": None,
                "original_token": None, "is_color": False}

    english = translate_color(token)
    if english:
        return {"base_name": base, "attribute_name": "color",
                "attribute_value": english, "original_token": token, "is_color": True}
    return {"base_name": base, "attribute_name": "model",
            "attribute_value": token, "original_token": token, "is_color": False}


def derive_catalog(sku, name, color=None):
    """Decide the main product + variant attribute for a scanned roll,
    handling both label families:

      • SKU encodes product.variant via a DOT ("K48083İ.G93")
        → main product = the part BEFORE the dot ("K48083İ"); the full SKU
          stays the variant_sku (set by the caller). Variant value = the
          scanned colour if OCR caught one, else the after-dot suffix.
      • SKU has no dot ("MRK00047") → main product + variant come from the
        NAME ("MT-3016 GÜMÜŞ" → MT-3016 / GÜMÜŞ) via parse_label_name.

    Returns {base_name, attribute_name, attribute_value, original_token, is_color}.
    """
    sku = (sku or "").strip()
    color = (color or "").strip()

    def _from_color(base, col):
        eng = translate_color(col)
        if eng:
            return {"base_name": base, "attribute_name": "color",
                    "attribute_value": eng, "original_token": col, "is_color": True}
        return {"base_name": base, "attribute_name": "model",
                "attribute_value": col, "original_token": col, "is_color": False}

    if "." in sku:
        base, _, suffix = sku.partition(".")
        base = base.strip()
        suffix = suffix.strip()
        if color:
            return _from_color(base, color)
        return {"base_name": base,
                "attribute_name": "model" if suffix else None,
                "attribute_value": suffix or None,
                "original_token": suffix or None, "is_color": False}

    parsed = parse_label_name(name)
    if color and not parsed["attribute_value"]:
        parsed = _from_color(parsed["base_name"], color)
    return parsed


def _to_decimal(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


@transaction.atomic
def sync_roll_to_catalog(*, base_name, attribute_name, attribute_value,
                         variant_sku, variant_barcode=None, quantity=None,
                         cost=None, existing_base_product=None):
    """Idempotently create/link a HIDDEN catalog Product (main) + ProductVariant
    (the scanned item). Returns (product, variant, product_created, variant_created).

    - quantity MIRRORS the warehouse stock onto the variant; the parent
      Product.quantity is recomputed as the sum of its variants' quantities.
    - Re-scanning the same variant_sku updates it in place (no duplicate).
    - Raises CatalogSyncConflict if variant_sku already belongs to another product.
    """
    from marketing.models import (
        Product, ProductVariant, ProductVariantAttribute,
        ProductVariantAttributeValue,
    )

    variant_sku = (variant_sku or "").strip()
    if not variant_sku:
        raise CatalogSyncConflict("variant_sku is required")

    base_name = (base_name or "").strip() or variant_sku
    qty = _to_decimal(quantity)
    cost_dec = _to_decimal(cost)

    # 1) Resolve / create the hidden base product. Never touch a featured
    #    (website-visible) product — keep the hidden catalog separate.
    product = existing_base_product
    if product is None:
        product = (Product.objects
                   .filter(title__iexact=base_name, featured=False)
                   .order_by("id").first())
    if product is None:
        product = Product.objects.create(
            title=base_name, sku=None, featured=False,
            unit_of_measurement="mt", quantity=Decimal("0"),
        )
        product_created = True
    else:
        product_created = False

    # 2) Lock the variant row (concurrent scans of the same roll are safe).
    existing = (ProductVariant.objects.select_for_update()
                .filter(variant_sku=variant_sku).first())
    if existing and existing.product_id != product.id:
        raise CatalogSyncConflict(
            f"variant_sku '{variant_sku}' already belongs to product "
            f"#{existing.product_id}, not '{base_name}' (#{product.id})."
        )

    if existing:
        variant = existing
        variant_created = False
        variant.variant_featured = False
        if qty is not None:
            variant.variant_quantity = qty          # mirror warehouse meters
        if variant_barcode and not variant.variant_barcode:
            variant.variant_barcode = variant_barcode[:14]
        if cost_dec is not None:
            variant.variant_cost = cost_dec
        variant.save(update_fields=[
            "variant_featured", "variant_quantity", "variant_barcode", "variant_cost",
        ])
    else:
        variant = ProductVariant.objects.create(
            product=product, variant_sku=variant_sku, variant_featured=False,
            variant_barcode=(variant_barcode or None) and variant_barcode[:14],
            variant_quantity=qty, variant_cost=cost_dec,
        )
        variant_created = True

    # 3) Attribute + value (pre-normalized so get_or_create matches existing rows).
    if attribute_name and attribute_value:
        attr, _ = ProductVariantAttribute.objects.get_or_create(
            name=_norm_attr(attribute_name))
        value_obj, _ = ProductVariantAttributeValue.objects.get_or_create(
            product_variant_attribute=attr,
            product_variant_attribute_value=_norm_value(attribute_value))
        # 4) Link M2M (idempotent via the through table).
        Through = ProductVariant.product_variant_attribute_values.through
        Through.objects.get_or_create(
            productvariant_id=variant.id,
            productvariantattributevalue_id=value_obj.id)

    # 5) Parent product stock = sum of its variants' stock.
    agg = (ProductVariant.objects.filter(product=product)
           .aggregate(s=Sum("variant_quantity")))
    product.quantity = agg["s"] or Decimal("0")
    product.save(update_fields=["quantity"])

    return product, variant, product_created, variant_created
