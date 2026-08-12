"""Backfill OrderItem.outsourced_quantity for lines saved before the
column existed.

Until now the create/edit order sidebar had nowhere to store the "depo
dışı" metres, so it folded them into the line's description as
"Depo dışı ilave: N m (not)". Billing never read that text — it bills
SCANNED metres — which meant an outsourced line on a product that
happens to be stocked in a warehouse was indistinguishable from a line
nobody had packed yet and silently vanished from the invoice and the
customer's cari.

This command reads those descriptions back into the real column and
re-posts the affected orders' cari movements so balances catch up.

Lines that need a HUMAN decision are reported, never guessed: a
warehouse-tracked line with no reservations and no "depo dışı" note is
either an outsourced line whose note was lost or a line that shipped
without ever being scanned. Only you know which.

    python manage.py backfill_outsourced_quantity            # dry run
    python manage.py backfill_outsourced_quantity --apply
    python manage.py backfill_outsourced_quantity --apply --order 265
"""
import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from operating.models import Order, OrderItem

# Matches what the sidebar used to write, e.g.
#   "Depo dışı ilave: 33.00 m"
#   "acele — Depo dışı ilave: 20.63 m (Bursa deposundan)"
NOTE_RE = re.compile(
    r"(?:\s*—\s*)?Depo dışı ilave:\s*([\d.,]+)\s*m(?:\s*\(([^)]*)\))?"
)


class Command(BaseCommand):
    help = "Backfill OrderItem.outsourced_quantity from legacy 'Depo dışı ilave' descriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Write the changes. Without it the command only reports.",
        )
        parser.add_argument(
            "--order", type=int, default=None,
            help="Limit to a single order pk.",
        )
        parser.add_argument(
            "--keep-note", action="store_true",
            help="Leave the 'Depo dışı ilave: N m' text in the description "
                 "instead of stripping it once the value has a real column.",
        )

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        keep_note = opts["keep_note"]

        items = (OrderItem.objects
                 .filter(outsourced_quantity__isnull=True)
                 .select_related("order", "product", "product_variant")
                 .order_by("order_id", "pk"))
        if opts["order"]:
            items = items.filter(order_id=opts["order"])

        parsed, touched_orders, unclear = [], set(), []
        for it in items:
            m = NOTE_RE.search(it.description or "")
            if not m:
                continue
            try:
                qty = Decimal(m.group(1).replace(",", "."))
            except (InvalidOperation, ValueError):
                self.stderr.write(f"  ! item {it.pk}: unparsable metres {m.group(1)!r}")
                continue
            note = (m.group(2) or "").strip()
            new_desc = it.description
            if not keep_note:
                new_desc = NOTE_RE.sub("", it.description or "").strip()
                new_desc = re.sub(r"^\s*—\s*", "", new_desc).strip()
                if note and note not in new_desc:
                    new_desc = f"{new_desc} — {note}" if new_desc else note
            parsed.append((it, qty, new_desc))
            touched_orders.add(it.order_id)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{len(parsed)} line(s) with a legacy 'depo dışı' note "
            f"across {len(touched_orders)} order(s)"
        ))
        for it, qty, new_desc in parsed:
            sku = (it.product_variant.variant_sku if it.product_variant_id
                   else (it.product.sku if it.product_id else "-"))
            self.stdout.write(
                f"  order {it.order_id:>5} item {it.pk:>5} {sku:<22} "
                f"qty={it.quantity} outsourced -> {qty}"
                + ("" if new_desc == it.description else f"  desc -> {new_desc!r}")
            )

        # Warehouse-tracked lines billing 0 that this backfill cannot
        # explain — surfaced so they can be corrected by hand.
        order_ids = ([opts["order"]] if opts["order"]
                     else list(OrderItem.objects.values_list("order_id", flat=True).distinct()))
        handled = {it.pk for it, _q, _d in parsed}
        for order in Order.objects.filter(pk__in=order_ids).prefetch_related("items"):
            line_items = list(order.items.all())
            if not line_items:
                continue
            tracked = order.classify_items_by_tracking(line_items)
            scanned = {
                r["order_item_id"]: (r["s"] or Decimal("0"))
                for r in (order.roll_reservations
                          .filter(order_item__isnull=False)
                          .values("order_item_id").annotate(s=Sum("meters")))
            }
            for it in line_items:
                if it.pk in handled or not tracked.get(it.pk):
                    continue
                if it.outsourced_quantity is not None:
                    continue
                if scanned.get(it.pk, Decimal("0")) > 0:
                    continue
                if (it.quantity or 0) <= 0:
                    continue
                unclear.append((order, it))

        if unclear:
            self.stdout.write(self.style.WARNING(
                f"\n{len(unclear)} tracked line(s) bill 0 and CANNOT be resolved "
                f"automatically — no rolls scanned and no 'depo dışı' note:"
            ))
            for order, it in unclear:
                sku = (it.product_variant.variant_sku if it.product_variant_id
                       else (it.product.sku if it.product_id else "-"))
                value = (it.quantity or 0) * (it.price or 0)
                self.stdout.write(
                    f"  order {order.pk:>5} ({order.order_status:<12}) item {it.pk:>5} "
                    f"{sku:<22} qty={it.quantity} x {it.price} = {value} unbilled"
                )
            self.stdout.write(
                "  → set outsourced_quantity on these by hand if the metres were "
                "sourced outside the warehouse, or scan/reserve the rolls if they "
                "came out of stock."
            )

        if not apply_changes:
            self.stdout.write(self.style.NOTICE("\nDry run — nothing written. Re-run with --apply."))
            return

        with transaction.atomic():
            for it, qty, new_desc in parsed:
                it.outsourced_quantity = qty
                it.description = new_desc
                it.save(update_fields=["outsourced_quantity", "description", "updated_at"])

        # Re-post the cari movements so balances reflect the new billable
        # totals. The OrderItem save signal already does this, but only
        # for orders that HAVE a cari — call explicitly and report.
        from current_account.services import post_order_movement
        repriced = 0
        for order in Order.objects.filter(pk__in=touched_orders, cari__isnull=False):
            try:
                mv = post_order_movement(order)
            except Exception as exc:
                self.stderr.write(f"  ! order {order.pk}: cari re-post failed — {exc}")
                continue
            repriced += 1
            self.stdout.write(
                f"  cari re-posted: order {order.pk} -> {mv.amount if mv else 0}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nBackfilled {len(parsed)} line(s); re-posted {repriced} cari movement(s)."
        ))
        self.stdout.write(
            "Invoices already issued are NOT rebuilt — reissue them if their "
            "totals need to change."
        )
