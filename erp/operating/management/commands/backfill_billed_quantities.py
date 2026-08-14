"""Freeze the billable quantities of orders that shipped before the
freeze existed.

What each line bills is derived from whether its SKU has a warehouse
entry (see Order.classify_items_by_tracking). A line with no warehouse
presence bills its full ordered quantity — nothing could ever be scanned
for it. The day stock for that SKU is received, the line becomes
scannable, and a shipped order (which will never be scanned again)
silently drops it to 0. Order #240 lost 245.00 across three lines that
way, weeks after it shipped, purely because unrelated stock arrived.

Order.billed_line_quantities stops that happening from now on. This
command repairs the orders that shipped before it existed, by replaying
each order's classification AS OF its ship date — warehouse entries
created after the order shipped are ignored, which is exactly the
picture the order billed from at the time.

Freezing moves no money on its own. It fixes what the order will report
from here on and stops further erosion. Correcting balances that already
drifted is --repost, deliberately a separate flag.

    python manage.py backfill_billed_quantities                  # dry run
    python manage.py backfill_billed_quantities --apply
    python manage.py backfill_billed_quantities --apply --repost
    python manage.py backfill_billed_quantities --apply --order 240
"""
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from operating.models import Order, OrderChange
from operating.views_warehouse import SHIPPED_CLASS


def _ship_moment(order):
    """When this order shipped, best-effort. shipped_at is authoritative;
    older rows predate that column, so fall back to the audit trail's
    last move into a shipped status, then to updated_at."""
    if order.shipped_at:
        return order.shipped_at, "shipped_at"
    change = (OrderChange.objects
              .filter(order_id=order.pk, action="status", field="order_status",
                      new_value__in=sorted(SHIPPED_CLASS))
              .order_by("-created_at").first())
    if change:
        return change.created_at, "audit"
    return order.updated_at, "updated_at"


def _value_of(order, qty_map):
    """Price × quantity per line, rounded per line like OrderItem.subtotal()."""
    total = Decimal("0.00")
    for it in order.items.all():
        qty = qty_map.get(it.pk, Decimal("0"))
        total += ((it.price or Decimal("0")) * qty).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    return total


class Command(BaseCommand):
    help = "Freeze billable quantities on orders that shipped before the freeze existed."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Write the freeze. Without this, only reports.")
        parser.add_argument("--repost", action="store_true",
                            help="Also re-post each order's cari movement to the frozen "
                                 "value. MOVES MONEY. Requires --apply.")
        parser.add_argument("--order", type=int, default=None,
                            help="Restrict to a single order id. Named explicitly, an "
                                 "already-frozen order is re-done rather than skipped.")
        parser.add_argument("--bill-ordered", action="store_true",
                            help="Freeze at the ORDERED quantities instead of "
                                 "reconstructing from scans — for an order that shipped "
                                 "without being scanned, where the ordered quantity is "
                                 "what actually went out. Requires --order, so this can "
                                 "only ever be a deliberate, per-order judgement.")

    def handle(self, *args, **opts):
        apply_ = opts["apply"]
        repost = opts["repost"]
        only = opts["order"]
        bill_ordered = opts["bill_ordered"]

        if repost and not apply_:
            self.stderr.write(self.style.ERROR("--repost requires --apply."))
            return
        if bill_ordered and not only:
            self.stderr.write(self.style.ERROR(
                "--bill-ordered requires --order: overriding what an order billed is a "
                "per-order judgement, never a sweep."))
            return

        qs = Order.objects.filter(order_status__in=SHIPPED_CLASS).order_by("pk")
        if only:
            # Naming an order is an explicit instruction to redo it, freeze or no.
            qs = qs.filter(pk=only)
        else:
            qs = qs.filter(billed_line_quantities__isnull=True)

        ct = ContentType.objects.get_for_model(Order)
        from accounting.models_accounts import CariMovement

        header = f"{'order':>6} {'ship basis':<11} {'now':>10} {'frozen':>10} {'recovers':>10} {'movement':>10}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        total_recovered = Decimal("0.00")
        changed = []

        for order in qs:
            as_of, basis = _ship_moment(order)
            if as_of is None:
                self.stdout.write(self.style.WARNING(
                    f"{order.pk:>6}  no ship date — skipped, needs a human"))
                continue

            if bill_ordered:
                frozen_map = {it.pk: (it.quantity or Decimal("0"))
                              for it in order.items.all()}
                basis = "ordered"
            else:
                frozen_map = order.compute_billable_line_quantities(as_of=as_of)
            live_map = order.compute_billable_line_quantities()
            frozen_val = _value_of(order, frozen_map)
            live_val = _value_of(order, live_map)
            delta = frozen_val - live_val

            mv = CariMovement.objects.filter(
                source_type=ct, source_id=order.pk, movement_type="order_sale",
            ).first()
            mv_txt = str(mv.amount) if mv else "—"

            style = self.style.SUCCESS if delta else (lambda s: s)
            self.stdout.write(style(
                f"{order.pk:>6} {basis:<11} {live_val:>10} {frozen_val:>10} "
                f"{delta:>10} {mv_txt:>10}"
            ))

            total_recovered += delta
            if delta:
                changed.append((order.pk, live_val, frozen_val, mv))

            if apply_:
                with transaction.atomic():
                    order.billed_line_quantities = {
                        str(k): str(v) for k, v in frozen_map.items()
                    }
                    order.billed_quantities_frozen_at = as_of
                    Order.objects.filter(pk=order.pk).update(
                        billed_line_quantities=order.billed_line_quantities,
                        billed_quantities_frozen_at=as_of,
                    )
                    if repost and order.cari_id:
                        from accounting.services_accounts import post_order_movement
                        post_order_movement(order)

        self.stdout.write("")
        self.stdout.write(f"orders examined : {qs.count()}")
        self.stdout.write(f"orders that drifted : {len(changed)}")
        self.stdout.write(f"receivable recovered by freezing : {total_recovered}")

        if not apply_:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — nothing written. Re-run with --apply to freeze, "
                "and --apply --repost to also correct the cari balances."))
        elif not repost:
            self.stdout.write(self.style.WARNING(
                "\nFrozen, but cari balances were NOT touched. The stored movement "
                "column above shows where they still disagree; --repost corrects them."))
