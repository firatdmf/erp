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
    - A different variant_sku that matches an EXISTING (product, attribute_name,
      attribute_value) is treated as the SAME logical variant: quantity is
      ADDED to it instead of forking a second ProductVariant, and its own
      variant_sku is left untouched.
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

    def _safe_sku(base):
        """The main-product SKU is the base code (K1245.G13 → 'K1245').
        Product.sku is globally unique, so never collide with another
        product's SKU — fall back to null if it's already taken."""
        b = (base or "").strip()[:20]
        if not b:
            return None
        if Product.objects.filter(sku__iexact=b).exists():
            return None
        return b

    # 1) Resolve / create the base product. A SKU match wins over
    #    everything: if ANY catalog product — featured web products
    #    included — carries the base code as its SKU, the variant
    #    belongs under it (warehouse "K12767.G28" → web product
    #    "Florenza" whose sku is "K12767"). Creating a parallel hidden
    #    product in that case is exactly the duplication we must avoid.
    #    Only then fall back to the hidden-by-title lookup, and lastly
    #    create a fresh hidden product.
    product = existing_base_product
    if product is None:
        b = (base_name or "").strip()
        if b:
            product = Product.objects.filter(sku__iexact=b).order_by("id").first()
    if product is None:
        product = (Product.objects
                   .filter(title__iexact=base_name, featured=False)
                   .order_by("id").first())
    if product is None:
        product = Product.objects.create(
            title=base_name, sku=_safe_sku(base_name), featured=False,
            unit_of_measurement="mt", quantity=Decimal("0"),
        )
        product_created = True
    else:
        product_created = False
        # Backfill the main-product SKU (the base code) on older hidden
        # products that were created before this without one.
        if not (product.sku or "").strip():
            new_sku = _safe_sku(product.title)
            if new_sku:
                product.sku = new_sku
                product.save(update_fields=["sku"])
        # Lock the product row for the rest of this transaction. There's no
        # DB constraint on (product, attribute_value) — only variant_sku is
        # globally unique — so without this, two concurrent syncs for the
        # SAME new (product, attribute) pair would both see no attr_matched
        # row below and both create(), forking a duplicate variant. Locking
        # the parent product serializes concurrent syncs onto it.
        Product.objects.select_for_update().filter(pk=product.id).first()

    # 2) Lock the variant row (concurrent scans of the same roll are safe).
    existing = (ProductVariant.objects.select_for_update()
                .filter(variant_sku=variant_sku).first())
    if existing and existing.product_id != product.id:
        raise CatalogSyncConflict(
            f"variant_sku '{variant_sku}' already belongs to product "
            f"#{existing.product_id}, not '{base_name}' (#{product.id})."
        )

    # 1b) Same logical variant under a DIFFERENT sku? A caller (e.g. the
    #     manual warehouse-intake form) may hand us a freshly minted
    #     variant_sku for what is actually a colour/model this product
    #     already carries — get_or_create-by-sku alone would then fork a
    #     second ProductVariant for it. Reuse the attribute-matched row
    #     instead, adding the incoming stock to it (unlike the mirror
    #     behaviour below, this quantity is genuinely NEW stock, not a
    #     restatement of the same roll/scan).
    attr_matched = False
    if existing is None and attribute_name and attribute_value:
        attr_matched = (ProductVariant.objects.select_for_update()
                        .filter(product=product,
                                product_variant_attribute_values__product_variant_attribute__name=_norm_attr(attribute_name),
                                product_variant_attribute_values__product_variant_attribute_value=_norm_value(attribute_value))
                        .first())
        if attr_matched:
            existing = attr_matched

    if existing:
        variant = existing
        variant_created = False
        # Never un-feature a REAL web product's variant — hiding it from
        # the storefront is not this sync's call. Hidden parents keep the
        # old behaviour.
        if not product.featured:
            variant.variant_featured = False
        if qty is not None:
            if attr_matched:
                # Matched by attribute, not by sku — this is additional
                # stock coming in under its own roll(s), not a restatement
                # of the matched variant's existing total.
                variant.variant_quantity = (variant.variant_quantity or Decimal("0")) + qty
            else:
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

    # 3) Attribute. A scanned product carries ONE attribute dimension
    #    (colour OR model) and ONE value. Enforce both:
    #      • LATEST value wins for THIS variant — re-scanning the same
    #        variant_sku with a new colour (blue → navy blue) REPLACES the
    #        old value instead of piling up "blue, navy_blue".
    #      • LATEST attribute TYPE wins for the whole product — mixing
    #        "color" and "model" on one product spawns a colour×model matrix
    #        of phantom variants, so every OTHER variant of the product is
    #        migrated onto this scan's dimension (each value's text is kept).
    # A FEATURED parent's attribute setup belongs to the web team — only
    # attach attributes to a variant we just created there, never rewire
    # its existing variants or replace a web variant's values.
    if attribute_name and attribute_value and (variant_created or not product.featured):
        Through = ProductVariant.product_variant_attribute_values.through
        target_attr, _ = ProductVariantAttribute.objects.get_or_create(
            name=_norm_attr(attribute_name))

        if not product.featured:
            # Migrate OTHER variants of this product off any different dimension.
            other_links = (Through.objects
                           .filter(productvariant__product=product)
                           .exclude(productvariant_id=variant.id)
                           .select_related("productvariantattributevalue"))
            for link in other_links:
                val = link.productvariantattributevalue
                if val.product_variant_attribute_id == target_attr.id:
                    continue
                moved, _ = ProductVariantAttributeValue.objects.get_or_create(
                    product_variant_attribute=target_attr,
                    product_variant_attribute_value=val.product_variant_attribute_value)
                Through.objects.get_or_create(
                    productvariant_id=link.productvariant_id,
                    productvariantattributevalue_id=moved.id)
                link.delete()

        # THIS variant: drop every old value, keep only the latest one.
        value_obj, _ = ProductVariantAttributeValue.objects.get_or_create(
            product_variant_attribute=target_attr,
            product_variant_attribute_value=_norm_value(attribute_value))
        Through.objects.filter(productvariant_id=variant.id).delete()
        Through.objects.get_or_create(
            productvariant_id=variant.id,
            productvariantattributevalue_id=value_obj.id)

    # 5) Parent product stock = sum of its variants' stock.
    agg = (ProductVariant.objects.filter(product=product)
           .aggregate(s=Sum("variant_quantity")))
    product.quantity = agg["s"] or Decimal("0")
    product.save(update_fields=["quantity"])

    return product, variant, product_created, variant_created


def resync_warehouse_product(wp, base_override=None):
    """Re-sync ONE warehouse product into the catalog after an edit
    (sku / name / main-product change).

    Re-links its catalog variant to the base product derived from the
    CURRENT sku — or to ``base_override`` (an explicit main-product title) —
    moving it OFF a wrong main product if needed and renaming the variant_sku
    to match the corrected warehouse sku. The variant's colour/model is
    preserved. Empty hidden products left behind are removed.

    Returns (variant, warning) — warning is a message string if the change
    couldn't be applied (e.g. the sku already belongs to another variant),
    in which case nothing is modified.
    """
    from django.db import transaction as _tx
    from marketing.models import Product, ProductVariant

    sku = (wp.sku or "").strip()
    if not sku:
        return None, None

    old = wp.catalog_variant
    # Refuse if the (possibly new) sku already belongs to a DIFFERENT variant
    # — don't silently merge or destroy the existing link.
    clash = (ProductVariant.objects.filter(variant_sku=sku)
             .exclude(pk=old.pk if old else 0).first())
    if clash:
        return None, (f"variant_sku '{sku}' zaten başka bir varyanta ait "
                      f"(ürün #{clash.product_id}).")

    with _tx.atomic():
        attr_name = attr_value = None
        if old:
            av = (old.product_variant_attribute_values
                  .select_related("product_variant_attribute").order_by("-id").first())
            if av:
                attr_name = av.product_variant_attribute.name
                attr_value = av.product_variant_attribute_value
            old_pid = old.product_id
            wp.catalog_variant = None
            wp.save(update_fields=["catalog_variant"])
            old.delete()
            if (Product.objects.filter(pk=old_pid, featured=False).exists()
                    and not ProductVariant.objects.filter(product_id=old_pid).exists()):
                Product.objects.filter(pk=old_pid).delete()

        cat = derive_catalog(sku, wp.name or "")
        base = (base_override or cat["base_name"] or "").strip()
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name=base,
            attribute_name=attr_name or cat["attribute_name"],
            attribute_value=attr_value or cat["attribute_value"],
            variant_sku=sku, variant_barcode=wp.barcode,
            quantity=wp.quantity, cost=wp.cost_usd,
        )
        wp.catalog_variant = variant
        wp.save(update_fields=["catalog_variant"])
        return variant, None


def rebuild_catalog_from_warehouse(warehouse=None, apply=True):
    """Reconstruct the hidden catalog from the warehouse (the source of truth).

    Early scans (before the grouping/İ/name-merge fixes) left the catalog
    tangled — variants filed under the wrong main product, blank main-product
    SKUs, garbled variant_skus. This rebuilds it deterministically from each
    warehouse product's CURRENT sku/name:

      * deletes the old (mis-grouped) catalog variant,
      * re-creates it under the CORRECT base product derived from the
        warehouse SKU (``K24620İ.G52`` → main product ``K24620İ``),
      * variant_sku = the warehouse SKU; main-product SKU = the base code,
      * the previous colour/model attribute is preserved,
      * hidden products left empty are removed.

    Idempotent — re-running yields the same result (the warehouse drives it).
    Pass apply=False for a dry-run that only reports the intended grouping.
    Returns a summary dict.
    """
    from django.db import transaction as _tx
    from operating.models import WarehouseProduct
    from marketing.models import Product, ProductVariant

    wps = (WarehouseProduct.objects
           .filter(catalog_variant__isnull=False)
           .select_related("catalog_variant__product"))
    if warehouse is not None:
        wps = wps.filter(warehouse=warehouse)

    # Snapshot every link BEFORE tearing anything down (so we keep colours).
    snaps, old_variant_ids, old_product_ids = [], set(), set()
    for wp in wps:
        v = wp.catalog_variant
        av = (v.product_variant_attribute_values
              .select_related("product_variant_attribute").order_by("-id").first())
        snaps.append({
            "wp": wp, "sku": (wp.sku or "").strip(), "name": wp.name or "",
            "barcode": wp.barcode, "qty": wp.quantity, "cost": wp.cost_usd,
            "attr_name": av.product_variant_attribute.name if av else None,
            "attr_value": av.product_variant_attribute_value if av else None,
        })
        old_variant_ids.add(v.id)
        old_product_ids.add(v.product_id)

    summary = {"warehouse_products": len(snaps), "rebuilt": 0,
               "deleted_variants": 0, "deleted_products": 0, "conflicts": []}

    if not apply:
        summary["plan"] = [
            {"variant_sku": s["sku"], "name": s["name"],
             "main_product": derive_catalog(s["sku"], s["name"])["base_name"]}
            for s in snaps]
        return summary

    with _tx.atomic():
        # 1) Unlink, then tear down the affected HIDDEN products ENTIRELY —
        #    every variant including orphans no warehouse product points at —
        #    and rebuild them from the warehouse below. Never touch a featured
        #    (website-visible) product.
        WarehouseProduct.objects.filter(
            pk__in=[s["wp"].pk for s in snaps]).update(catalog_variant=None)
        hidden_pids = list(Product.objects.filter(
            id__in=old_product_ids, featured=False).values_list("id", flat=True))
        if hidden_pids:
            summary["deleted_variants"] = ProductVariant.objects.filter(
                product_id__in=hidden_pids).delete()[0]
            summary["deleted_products"] = Product.objects.filter(
                id__in=hidden_pids).delete()[0]

        # 2) Re-sync each warehouse product into the correct catalog shape.
        for s in snaps:
            if not s["sku"]:
                continue
            cat = derive_catalog(s["sku"], s["name"])
            try:
                _p, variant, _pc, _vc = sync_roll_to_catalog(
                    base_name=cat["base_name"],
                    attribute_name=s["attr_name"] or cat["attribute_name"],
                    attribute_value=s["attr_value"] or cat["attribute_value"],
                    variant_sku=s["sku"], variant_barcode=s["barcode"],
                    quantity=s["qty"], cost=s["cost"],
                )
                s["wp"].catalog_variant = variant
                s["wp"].save(update_fields=["catalog_variant"])
                summary["rebuilt"] += 1
            except CatalogSyncConflict as exc:
                summary["conflicts"].append({"sku": s["sku"], "error": str(exc)})

    return summary
