# -*- coding: utf-8 -*-
"""Reconcile EVERY WarehouseProduct with the marketing catalog — link by
SKU, create what's missing, fix wrong links. No exceptions.

Matching ladder per distinct warehouse SKU (exact case-insensitive
first, Turkish-fold alphanumeric-only comparison as fallback):

  1. A ProductVariant already carries this SKU → link to it. If it sits
     under an auto-created hidden product while a REAL product owns the
     base code as its SKU (warehouse "K12767.G93" vs web product
     "Florenza" whose sku is "K12767"), the variant is MOVED under the
     real product — variant id preserved, so existing order lines keep
     pointing at it.
  2. Else a Product owns the base code as its SKU → create the variant
     under it (variant_featured=False so it never leaks onto the site).
  3. Else fall back to a hidden product matched by title, creating one
     when nothing exists.

Existing variants of FEATURED products are never re-featured,
re-attributed or moved away — only their stock mirror is updated.
Quantity mirror: variant_quantity = SUM over every warehouse row
sharing the SKU; each touched parent's quantity = sum of its variants.
Hidden products left with zero variants after moves are deleted.

Ambiguities are REPORTED in the summary's `conflicts`, never guessed.
"""
from decimal import Decimal

from django.db.models import Sum

from .catalog_sync import _fold, _norm_attr, _norm_value, derive_catalog


def _norm(s):
    s = _fold((s or "").strip())
    return "".join(ch for ch in s if ch.isalnum())


def reconcile_all_warehouse_links(apply=False, skus=None):
    """apply=False → dry-run (no writes) returning the same summary.
    skus=[...] restricts to those warehouse SKUs (import hook); None = all.
    """
    from django.db import transaction as _tx
    from operating.models import WarehouseProduct
    from marketing.models import (
        Product, ProductVariant, ProductVariantAttribute,
        ProductVariantAttributeValue,
    )

    wps_all = list(WarehouseProduct.objects.all()
                   .select_related("catalog_variant__product"))
    if skus is not None:
        wanted = {(s or "").strip().lower() for s in skus if (s or "").strip()}
        wps_all = [w for w in wps_all if (w.sku or "").strip().lower() in wanted]

    groups = {}
    for wp in wps_all:
        k = (wp.sku or "").strip().lower()
        if not k:
            continue
        groups.setdefault(k, []).append(wp)

    # Lookup maps.
    all_variants = list(ProductVariant.objects.select_related("product"))
    v_exact = {(v.variant_sku or "").strip().lower(): v for v in all_variants}
    v_fold = {}
    for v in all_variants:
        v_fold.setdefault(_norm(v.variant_sku), []).append(v)
    all_products = list(Product.objects.all())
    p_sku_exact = {(p.sku or "").strip().lower(): p
                   for p in all_products if (p.sku or "").strip()}
    p_sku_fold = {}
    for p in all_products:
        if (p.sku or "").strip():
            p_sku_fold.setdefault(_norm(p.sku), []).append(p)
    p_title_hidden = {}
    for p in all_products:
        if not p.featured and (p.title or "").strip():
            p_title_hidden.setdefault((p.title or "").strip().lower(), p)

    summary = {
        "groups": len(groups), "linked_wps": 0, "relinked_wps": 0,
        "variants_created": 0, "variants_moved": 0,
        "products_created": 0, "products_deleted": 0,
        "conflicts": [], "actions": [],
    }
    touched_product_ids = set()
    maybe_empty_product_ids = set()

    def find_variant(sku_l, sku_n):
        v = v_exact.get(sku_l)
        if v:
            return v, None
        cands = v_fold.get(sku_n) or []
        if len(cands) == 1:
            return cands[0], "fold"
        if len(cands) > 1:
            return None, "ambiguous"
        return None, None

    def find_parent(base):
        p = p_sku_exact.get(base.strip().lower())
        if p:
            return p
        cands = p_sku_fold.get(_norm(base)) or []
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1:
            feat = [c for c in cands if c.featured]
            return sorted(feat or cands, key=lambda c: c.id)[0]
        return None

    for k, group in sorted(groups.items()):
        wp0 = group[0]
        sku = (wp0.sku or "").strip()
        cat = derive_catalog(sku, wp0.name or "")
        base = (cat["base_name"] or sku).strip()

        total_qty = Decimal("0")
        for w in group:
            total_qty += (w.quantity or Decimal("0"))
        cost = next((w.cost_usd for w in group if w.cost_usd), None)
        barcode = next((w.barcode for w in group if w.barcode), None)

        variant, v_how = find_variant(k, _norm(sku))
        if v_how == "ambiguous":
            summary["conflicts"].append(
                {"sku": sku, "error": "birden fazla varyant fold-eşleşmesi — elle inceleyin"})
            continue
        parent = find_parent(base)

        try:
            if variant is not None:
                target = parent or variant.product
                if variant.product_id != target.id:
                    if variant.product.featured:
                        # Never yank a variant off a real web product.
                        summary["conflicts"].append(
                            {"sku": sku,
                             "error": (f"varyant featured ürün '{variant.product.title}' altında; "
                                       f"sku-eşleşen '{target.title}' ile çelişiyor — taşınmadı")})
                        target = variant.product
                    else:
                        maybe_empty_product_ids.add(variant.product_id)
                        summary["variants_moved"] += 1
                        summary["actions"].append(
                            f"MOVE {variant.variant_sku}: '{variant.product.title}' -> '{target.title}'")
                        if apply:
                            variant.product = target
                            variant.save(update_fields=["product"])
                # Stock mirror only — never touch a pre-existing variant's
                # featured flag or attributes here.
                if apply:
                    variant.variant_quantity = total_qty
                    upd = ["variant_quantity"]
                    if cost is not None and variant.variant_cost is None:
                        variant.variant_cost = cost
                        upd.append("variant_cost")
                    variant.save(update_fields=upd)
                touched_product_ids.add(target.id)
            else:
                if parent is None:
                    parent = p_title_hidden.get(base.lower())
                if parent is None:
                    summary["products_created"] += 1
                    summary["actions"].append(f"NEW PRODUCT '{base}' (hidden) for {sku}")
                    if apply:
                        taken = Product.objects.filter(sku__iexact=base[:20]).exists()
                        parent = Product.objects.create(
                            title=base, sku=(None if taken else (base[:20] or None)),
                            featured=False, unit_of_measurement="mt",
                            quantity=Decimal("0"),
                        )
                        if parent.sku:
                            p_sku_exact[parent.sku.strip().lower()] = parent
                        p_title_hidden[base.lower()] = parent
                summary["variants_created"] += 1
                summary["actions"].append(
                    f"NEW VARIANT {sku} under '{parent.title if parent else base}'")
                if apply:
                    variant = ProductVariant.objects.create(
                        product=parent, variant_sku=sku[:20],
                        variant_featured=False,
                        variant_barcode=(barcode or None) and barcode[:14],
                        variant_quantity=total_qty, variant_cost=cost,
                    )
                    v_exact[sku.lower()] = variant
                    # Colour/model attribute — attached to THIS variant only.
                    if cat["attribute_name"] and cat["attribute_value"]:
                        attr, _c = ProductVariantAttribute.objects.get_or_create(
                            name=_norm_attr(cat["attribute_name"]))
                        val, _c = ProductVariantAttributeValue.objects.get_or_create(
                            product_variant_attribute=attr,
                            product_variant_attribute_value=_norm_value(cat["attribute_value"]))
                        variant.product_variant_attribute_values.add(val)
                    touched_product_ids.add(parent.id)

            if apply and variant is not None:
                for w in group:
                    if w.catalog_variant_id != variant.id:
                        summary["relinked_wps"] += 1
                    w.catalog_variant = variant
                WarehouseProduct.objects.bulk_update(group, ["catalog_variant"])
            summary["linked_wps"] += len(group)
        except Exception as exc:
            summary["conflicts"].append({"sku": sku, "error": str(exc)})

    if apply:
        with _tx.atomic():
            # Parent stock = sum of variants (warehouse is the truth).
            for pid in touched_product_ids:
                agg = (ProductVariant.objects.filter(product_id=pid)
                       .aggregate(s=Sum("variant_quantity")))
                if agg["s"] is not None:
                    Product.objects.filter(pk=pid).update(quantity=agg["s"])
            # Hidden products left empty after moves → remove the husks.
            for pid in maybe_empty_product_ids:
                try:
                    p = Product.objects.filter(pk=pid, featured=False).first()
                    if p and not ProductVariant.objects.filter(product_id=pid).exists():
                        p.delete()
                        summary["products_deleted"] += 1
                except Exception:
                    pass  # e.g. protected by an order line — leave it

    return summary
