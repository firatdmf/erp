# -*- coding: utf-8 -*-
"""Link every WarehouseProduct to the marketing catalog.

The invariant the warehouse assumes — every physical product has a
catalog_variant behind it — was only ever enforced on ONE of the five
paths that create warehouse rows: the Excel import view, which calls
`reconcile_all_warehouse_links` for the SKUs it touched. Goods receipt,
manual stock-item entry, warehouse transfer and `import_ergene_stock` all
leave `catalog_variant` NULL, and nothing swept up after them, so the
rows they created never appear anywhere the catalog is the join.

This is that sweep, and the tool to re-run whenever the two drift.

Dry run by default — it reports exactly what --apply would do:

    python manage.py reconcile_catalog                 # preview
    python manage.py reconcile_catalog --actions       # ...line by line
    python manage.py reconcile_catalog --apply
    python manage.py reconcile_catalog --apply --sku K12504.G07 --sku N1539.G54

Matching, conflicts and the "never yank a variant off a featured web
product" rule all live in operating/catalog_reconcile.py; this command
only chooses the scope and prints the summary.
"""
from django.core.management.base import BaseCommand

from operating.catalog_reconcile import reconcile_all_warehouse_links


class Command(BaseCommand):
    help = ("Link every WarehouseProduct to a marketing ProductVariant, "
            "creating the hidden products/variants that are missing. "
            "Dry run unless --apply.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Commit. Without it nothing is written.")
        parser.add_argument(
            "--sku", action="append", dest="skus", metavar="SKU",
            help="Restrict to this warehouse SKU. Repeatable; default is all.")
        parser.add_argument(
            "--actions", action="store_true",
            help="List every individual change, not just the totals.")
        parser.add_argument(
            "--limit-actions", type=int, default=40, metavar="N",
            help="With --actions, print at most N lines (0 = all). Default 40.")

    def handle(self, *args, **opts):
        w = self.stdout.write
        skus = opts.get("skus")
        apply = opts["apply"]

        if skus:
            w(f"Reconciling {len(skus)} SKU(s): {', '.join(skus)}")
        else:
            w("Reconciling every warehouse product against the catalog.")

        s = reconcile_all_warehouse_links(apply=apply, skus=skus)

        w("")
        w(f"  distinct SKUs examined  {s['groups']:>7}")
        w(f"  warehouse rows linked   {s['linked_wps']:>7}")
        w(f"  ...whose link changed   {s['relinked_wps']:>7}")
        w(f"  variants created        {s['variants_created']:>7}")
        w(f"  variants moved          {s['variants_moved']:>7}")
        w(f"  hidden products created {s['products_created']:>7}")
        w(f"  empty products deleted  {s['products_deleted']:>7}")

        if opts["actions"] and s["actions"]:
            limit = opts["limit_actions"]
            shown = s["actions"] if limit <= 0 else s["actions"][:limit]
            w("")
            for line in shown:
                w(f"    {line}")
            if len(shown) < len(s["actions"]):
                w(f"    ... and {len(s['actions']) - len(shown)} more "
                  f"(--limit-actions 0 for all)")

        if s["conflicts"]:
            w("")
            w(self.style.WARNING(
                f"  {len(s['conflicts'])} SKU(s) need a HUMAN decision and were "
                f"left exactly as they are:"))
            for c in s["conflicts"]:
                w(f"    {c['sku']}: {c['error']}")

        w("")
        if apply:
            w(self.style.SUCCESS("Applied."))
        else:
            w(self.style.WARNING(
                "DRY RUN — nothing was written. Re-run with --apply."))
