# -*- coding: utf-8 -*-
"""Remove the home-textile catalogue that was bulk-loaded on 2026-07-06.

4,664 ProductVariants under 346 Products, all landed in one day and never
touched since. They are not Demfirat goods: the variant attributes are duvet
cover sets, bathrobes and satin 300TC sets, the "product" titles are company
names (GÜRSAN, DOĞRUYOL, NURPAK, PENTA, CRETON, ÇEŞTEPE, HASPEN), and most
carry EAN-13 retail barcodes. It reads as a supplier or trade-fair price list
loaded into the catalog. `unit_of_measurement` is "mt" on every one of them —
metres, for bathrobes — which is the tell of a bulk load that took the default.

They are inert but they are 68% of the variant table, so they distort every
count anyone runs.

Selected by SKU shape (one or two letters then 7+ digits) AND never carried by
a warehouse. Every other condition below is a GUARD, not a filter: the set was
measured to have no featured rows, no prices, and nothing referencing it, so a
row failing a guard means the shape has caught something real and the command
should skip it rather than widen. Two pattern-matching variants ARE stocked and
fall outside the selection on the warehouse test alone.

Products are not selected directly — only deleted afterwards if the purge left
them with no variants at all, and even then only when nothing else is hanging
off them. That spares the four mixed products that carry a few stray legacy
variants alongside real ones: LOVE (#240, featured, 4 images), KADİFE (#1096,
8 stocked variants and an order line), DMF (#1170, stocked) and ADEM (#1260).

Everything removed is written to ~/Backups/erp/ as JSON first, keyed by row id,
so it can be put back.

Dry run by default; --apply commits.

    python manage.py purge_legacy_catalog_import
    python manage.py purge_legacy_catalog_import --apply
"""
import datetime
import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

SKU_SHAPE = r"^[A-Z]{1,2}[0-9]{7,}$"
BACKUP_DIR = os.path.expanduser("~/Backups/erp")


class Command(BaseCommand):
    help = ("Delete the 2026-07-06 bulk-imported home-textile catalogue "
            "(variants + the products it leaves empty). Dry run unless --apply.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")
        parser.add_argument("--backup-dir", default=BACKUP_DIR,
                            help=f"Where the JSON snapshot goes (default {BACKUP_DIR}).")

    def handle(self, *args, **opts):
        from marketing.models import Product, ProductVariant

        w = self.stdout.write
        apply = opts["apply"]

        # Shape + never-in-a-warehouse is the selection. Everything else is a guard.
        candidates = (ProductVariant.objects
                      .filter(variant_sku__regex=SKU_SHAPE,
                              warehouse_products__isnull=True)
                      .select_related("product"))

        # Any of these means the shape has caught something real. Resolved in
        # SQL rather than per row, so the guard cannot be defeated by 4,664
        # round trips timing out half way.
        GUARDS = (Q(variant_featured=True) | Q(variant_price__isnull=False)
                  | Q(orderitem__isnull=False) | Q(invoice_items__isnull=False)
                  | Q(wip_goods__isnull=False))
        spared = candidates.filter(GUARDS).distinct()
        doomed_qs = candidates.exclude(pk__in=spared.values("pk"))

        n_spared = spared.count()
        doomed_ids = list(doomed_qs.values_list("pk", flat=True))
        w(f"  variants matching the shape, never stocked : {len(doomed_ids) + n_spared}")
        w(f"  to delete                                  : {len(doomed_ids)}")
        if n_spared:
            w(self.style.WARNING(
                f"  SPARED (a guard fired — the shape caught something real): {n_spared}"))
            for v in spared.select_related("product")[:10]:
                why = []
                if v.variant_featured:
                    why.append("variant_featured")
                if v.variant_price is not None:
                    why.append("has a price")
                if v.orderitem_set.exists():
                    why.append("on an order line")
                if v.invoice_items.exists():
                    why.append("on an invoice line")
                if v.wip_goods.exists():
                    why.append("work in progress")
                w(f"      {v.variant_sku} ({v.product.title}): {', '.join(why)}")

        touched_product_ids = set(
            doomed_qs.values_list("product_id", flat=True))

        # A product goes only if the purge empties it AND nothing else holds it.
        empty_after = (Product.objects
                       .filter(pk__in=touched_product_ids)
                       .annotate(surviving=Count("variants",
                                                 filter=~Q(variants__pk__in=doomed_ids)))
                       .filter(surviving=0, featured=False)
                       .annotate(n_files=Count("files", distinct=True),
                                 n_orders=Count("orderitem", distinct=True))
                       .filter(n_files=0, n_orders=0))
        empty_ids = list(empty_after.values_list("pk", flat=True))

        spared_products = sorted(touched_product_ids - set(empty_ids))
        w(f"  products emptied and removed               : {len(empty_ids)}")
        w(f"  products kept (still hold something)       : {len(spared_products)}")
        for p in Product.objects.filter(pk__in=spared_products)[:10]:
            w(f"      #{p.pk} {p.title!r} keeps "
              f"{p.variants.exclude(pk__in=doomed_ids).count()} variant(s)")

        if not doomed_ids:
            w("\nNothing to do.")
            return

        path = self._snapshot(doomed_ids, empty_ids, opts["backup_dir"], apply, w)

        if not apply:
            w("")
            w(self.style.WARNING("DRY RUN — nothing was written. Re-run with --apply."))
            return

        with transaction.atomic():
            v_deleted = ProductVariant.objects.filter(pk__in=doomed_ids).delete()
            p_deleted = Product.objects.filter(pk__in=empty_ids).delete()
        w("")
        w(f"  deleted variants : {v_deleted[0]} rows {dict(v_deleted[1])}")
        w(f"  deleted products : {p_deleted[0]} rows {dict(p_deleted[1])}")
        w(self.style.SUCCESS(f"\nApplied. Snapshot: {path}"))

    def _snapshot(self, variant_ids, product_ids, backup_dir, apply, w):
        """Write everything about to go to JSON, keyed by id, before it goes."""
        from marketing.models import Product, ProductVariant

        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        path = os.path.join(backup_dir, f"legacy-catalog-import-purged-{stamp}.json")

        variants = []
        for v in (ProductVariant.objects.filter(pk__in=variant_ids)
                  .prefetch_related("product_variant_attribute_values__product_variant_attribute")):
            variants.append({
                "id": v.pk, "product_id": v.product_id,
                "variant_sku": v.variant_sku, "variant_barcode": v.variant_barcode,
                "variant_cost": str(v.variant_cost) if v.variant_cost is not None else None,
                "variant_price": str(v.variant_price) if v.variant_price is not None else None,
                "variant_featured": v.variant_featured,
                "attributes": [
                    {"name": av.product_variant_attribute.name,
                     "value": av.product_variant_attribute_value}
                    for av in v.product_variant_attribute_values.all()
                ],
            })
        products = [
            {"id": p.pk, "title": p.title, "sku": p.sku, "featured": p.featured,
             "barcode": p.barcode, "type": p.type,
             "unit_of_measurement": p.unit_of_measurement,
             "category_id": p.category_id, "supplier_account_id": p.supplier_account_id,
             "cost": str(p.cost) if p.cost is not None else None,
             "price": str(p.price) if p.price is not None else None,
             "description": p.description}
            for p in Product.objects.filter(pk__in=product_ids)
        ]
        doc = {
            "taken_at": datetime.datetime.now().isoformat(),
            "note": ("Home-textile catalogue bulk-loaded 2026-07-06 and purged. "
                     "Variants and the products the purge emptied, keyed by id."),
            "counts": {"variants": len(variants), "products": len(products)},
            "product_variants": variants, "products": products,
        }
        if apply:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=1)
            w(f"  snapshot written : {path}")
        else:
            w(f"  snapshot would be written to: {path}")
        return path
