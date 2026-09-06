"""Recover Order.created_by from the audit trail.

Order.created_by was added after these orders existed, so every row
predating it is NULL and the detail page reads "Creator not recorded".
The information is not lost, though: operating/audit.py has been writing
an OrderChange(action="created") row — carrying the acting user — since
long before the column existed, so for most orders the original author
can be read straight back out.

Only the definitive source is used. An order is backfilled ONLY from its
own action="created" audit row. Orders that have other audit rows but no
"created" one are deliberately left alone: the earliest row there
records whoever next TOUCHED the order, which is not the same claim, and
a plausible-looking wrong author is worse than an honest blank.

Idempotent — it only ever fills a NULL — so re-running is safe.

    python manage.py backfill_order_creators            # dry run
    python manage.py backfill_order_creators --commit
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from operating.models import Order, OrderChange


class Command(BaseCommand):
    help = "Fill Order.created_by from OrderChange(action='created') rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit", action="store_true",
            help="Actually write. Without it, nothing is saved.",
        )

    def handle(self, *args, **opts):
        commit = opts["commit"]

        targets = list(Order.objects.filter(created_by__isnull=True))
        if not targets:
            self.stdout.write(self.style.SUCCESS(
                "Every order already has a creator. Nothing to do."
            ))
            return

        # One query for the evidence, keyed by order. Oldest first so that
        # if an order somehow carries two "created" rows, the first one
        # wins — the later one cannot be the creation.
        evidence = {}
        rows = (OrderChange.objects
                .filter(action="created", created_by__isnull=False,
                        order_id__in=[o.pk for o in targets])
                .order_by("created_at")
                .values_list("order_id", "created_by_id"))
        for order_id, user_id in rows:
            evidence.setdefault(order_id, user_id)

        fixable = [o for o in targets if o.pk in evidence]
        unknown = [o for o in targets if o.pk not in evidence]

        for order in fixable:
            order.created_by_id = evidence[order.pk]

        if commit:
            with transaction.atomic():
                Order.objects.bulk_update(fixable, ["created_by"])
            self.stdout.write(self.style.SUCCESS(
                f"Backfilled {len(fixable)} order(s)."
            ))
        else:
            self.stdout.write(
                f"DRY RUN — would backfill {len(fixable)} order(s). "
                "Re-run with --commit to write."
            )

        by_user = {}
        for order in fixable:
            by_user[order.created_by_id] = by_user.get(order.created_by_id, 0) + 1
        if by_user:
            from django.contrib.auth.models import User

            names = {u.pk: (u.get_full_name() or u.username)
                     for u in User.objects.filter(pk__in=by_user)}
            self.stdout.write("  attributed to:")
            for user_id, count in sorted(by_user.items(), key=lambda kv: -kv[1]):
                self.stdout.write(f"    {names.get(user_id, user_id)}: {count}")

        if unknown:
            self.stdout.write(self.style.WARNING(
                f"  {len(unknown)} order(s) have no 'created' audit row and stay "
                f"blank: {', '.join(str(o.pk) for o in unknown[:20])}"
                + (" …" if len(unknown) > 20 else "")
            ))
            self.stdout.write(
                "  Those predate the audit trail. Attributing them from a later "
                "edit would name whoever touched them next, not who raised them."
            )
