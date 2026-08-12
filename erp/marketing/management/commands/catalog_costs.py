"""Report catalog cost coverage and drift against the warehouse.

Read-only. Nothing here writes — it exists so you can see what has to be
filled in before generating a priced catalog, and where a hand-entered cost
disagrees with what the warehouse paid.

    python manage.py catalog_costs                          # coverage summary
    python manage.py catalog_costs --missing                # only what needs a cost
    python manage.py catalog_costs --drift                  # only disagreements
    python manage.py catalog_costs --category ready-made_curtain

Cost model, as decided:

  * marketing ProductVariant.variant_cost (or Product.cost for a product with
    no variants) is the AUTHORITATIVE pricing input. It is the only field that
    covers outsourced products, which have no warehouse row at all — 28 of the
    55 featured products.
  * The warehouse figure is a REFERENCE for comparison, never an automatic
    overwrite. Repricing stays a decision.
  * The basis is REPLACEMENT cost — what the next roll costs — not an average
    over stock held, so prices do not sag as cheap old stock sells down.

    NOTE: WarehouseProductRoll has no cost column yet, so "warehouse cost"
    below is the parent WarehouseProduct.cost_usd — which today IS the single
    cost shared by every roll. Once per-roll cost lands this should read the
    newest roll instead; that is the only line that needs to change.

All costs are USD (see marketing.catalog_builder.BASE_CURRENCY).
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

# Below this, a difference is rounding noise rather than a real disagreement.
DRIFT_EPSILON = Decimal("0.01")


class Command(BaseCommand):
    help = "Report catalog cost coverage and drift vs the warehouse (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--category", default="", help="Limit to one product category.")
        parser.add_argument("--missing", action="store_true", help="Only rows lacking a cost.")
        parser.add_argument("--drift", action="store_true", help="Only rows disagreeing with the warehouse.")

    def handle(self, *args, **options):
        from marketing.catalog_builder import catalog_queryset
        from operating.models import WarehouseProduct

        products = catalog_queryset(category=options["category"])

        # One query for every warehouse cost we might need, keyed by variant.
        warehouse_cost = {}
        rows = (WarehouseProduct.objects
                .filter(catalog_variant__product__in=products, cost_usd__isnull=False)
                .values_list("catalog_variant_id", "cost_usd", "updated_at"))
        for variant_id, cost, updated in rows:
            # Newest wins — replacement cost, not an average of what is held.
            previous = warehouse_cost.get(variant_id)
            if previous is None or updated > previous[1]:
                warehouse_cost[variant_id] = (cost, updated)

        agreeing = differing = unverified = missing = 0
        printed_any = False

        for product in products:
            variants = list(product.variants.all())
            lines = []

            if not variants:
                # A product with no variants prices off Product.cost.
                cost = product.cost
                lines.append((product.sku or "—", cost, None))
            else:
                for variant in variants:
                    reference = warehouse_cost.get(variant.id)
                    lines.append((
                        variant.variant_sku,
                        variant.variant_cost,
                        reference[0] if reference else None,
                    ))

            shown = []
            for sku, cost, reference in lines:
                if cost is None:
                    missing += 1
                    state, note = "MISSING", "no cost — cannot be priced by markup"
                elif reference is None:
                    # No warehouse row to compare against. Calling this "OK"
                    # would claim a confirmation we never made — an outsourced
                    # product has nothing to check against, and a stocked one
                    # may simply not be linked yet.
                    unverified += 1
                    state, note = "NO REF", f"catalog ${cost} — no warehouse row to compare"
                elif abs(Decimal(cost) - Decimal(reference)) > DRIFT_EPSILON:
                    differing += 1
                    # Deliberately NOT phrased as a delta FROM the warehouse.
                    # Either side can be the stale one: Vienna's gold variant is
                    # correctly $2.30 while its warehouse row still says $1.70,
                    # the same as the silvers. Show both, let a human judge.
                    state, note = "DIFFERS", f"catalog ${cost}   warehouse ${reference}"
                else:
                    agreeing += 1
                    state, note = "AGREES", f"${cost}"

                if options["missing"] and state != "MISSING":
                    continue
                if options["drift"] and state != "DIFFERS":
                    continue
                shown.append((sku, state, note))

            if not shown:
                continue
            printed_any = True
            self.stdout.write(f"\n{product.title or product.sku}  ({product.category or 'no category'})")
            for sku, state, note in shown:
                style = {
                    "AGREES": self.style.SUCCESS,
                    "DIFFERS": self.style.WARNING,
                    "NO REF": self.style.HTTP_INFO,
                }.get(state, self.style.ERROR)
                self.stdout.write(f"   {style(state.ljust(7))} {str(sku)[:20]:20s} {note}")

        if not printed_any:
            self.stdout.write("Nothing matches that filter.")

        total = agreeing + differing + unverified + missing
        self.stdout.write("")
        self.stdout.write(f"{total} sellable line(s) across {len(products)} product(s)")
        self.stdout.write(self.style.SUCCESS(f"  {agreeing} agree with the warehouse"))
        if differing:
            self.stdout.write(self.style.WARNING(
                f"  {differing} differ — check BOTH sides; the warehouse row can be the stale one"))
        if unverified:
            self.stdout.write(self.style.HTTP_INFO(
                f"  {unverified} have a cost but no warehouse row to check against"))
        if missing:
            self.stdout.write(self.style.ERROR(
                f"  {missing} missing — these DISAPPEAR from a catalog generated with ?markup="))
