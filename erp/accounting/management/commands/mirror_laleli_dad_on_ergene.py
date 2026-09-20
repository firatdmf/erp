"""Give Ergene its half of the four events Laleli booked against "DAD".

DAD (Laleli CARI-084) was a temporary account standing in for Ergene — the
account Laleli really keeps for its sister book is DEMFIRAT KARVEN | ERGENE
(KARFF). Four events went to the stand-in instead, and because they never
touched the paired account, Ergene never got its mirroring half:

    1148  2026-08-28  payment      +744.00   PAY-2026-000086
    1485  2026-09-14  payment    +5,000.00   PAY-2026-000113
    1562  2026-09-16  adjustment −5,000.00   TRA-2026-000019
    1608  2026-09-17  collection     −4.11   COL-2026-000120
                                    739.89

The two inter-company accounts currently mirror to the cent (±33,732.00)
ONLY because both books omitted these four symmetrically. Merging DAD into
KARFF moves 739.89 onto Laleli's side and breaks that; this writes the four
counterparts that put it back, at 32,992.11 each way.

WHY THIS IS DONE BY HAND, when a mirror machine exists
------------------------------------------------------
ACC-065 and KARFF are paired (services_mirror.pair_accounts), mirror_since
= 2026-09-15 22:54:27. Two things follow, and both are traps:

  * `is_mirrored` requires created_at >= mirror_since, and these four
    straddle it — 1148 and 1485 were written before the pairing, 1562 and
    1608 after. Re-saving all four through the signal would mirror two and
    silently skip two, leaving the books 5,744.00 apart, which is exactly
    744.00 + 5,000.00. Half a fix looks like a whole one.
  * dedupe_current_accounts._merge re-points rows with a queryset
    .update(), which fires no post_save at all, so in practice the merge
    mirrors NONE of them. Either way the four need writing explicitly.

The rows match the convention of the fourteen mirrors already on ACC-065 —
reference LAL-<laleli id>, description "Laleli: <document> · <text>" — and
not services_mirror's own ("Mirror of ..."), because they are backfilling
that same hand-made set. Anything written on KARFF from now on will mirror
itself automatically; nothing in the system carries mirror_of yet.

Idempotent on the LAL-<id> reference. Dry run by default; --apply commits.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Book
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement

ERGENE_ACCOUNT = 1622          # ACC-065 DEMFIRAT | Laleli
LALELI_PARTNER = 142           # KARFF   DEMFIRAT KARVEN | ERGENE
LALELI_ROWS = [1148, 1485, 1562, 1608]


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Write Ergene's half of the four Laleli DAD movements."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        w = self.stdout.write
        ergene = CurrentAccount.objects.select_related("book").get(pk=ERGENE_ACCOUNT)
        partner = CurrentAccount.objects.select_related("book").get(pk=LALELI_PARTNER)

        originals = list(CurrentAccountMovement.objects
                         .filter(pk__in=LALELI_ROWS)
                         .select_related("current_account", "currency")
                         .order_by("date", "pk"))
        if len(originals) != len(LALELI_ROWS):
            found = {o.pk for o in originals}
            raise CommandError(f"Missing Laleli rows: {sorted(set(LALELI_ROWS) - found)}")

        w(f"Ergene account : {ergene.code} {ergene.name!r}  balance {ergene.cached_balance}")
        w(f"Laleli partner : {partner.code} {partner.name!r}  balance {partner.cached_balance}")
        w("")

        made, skipped, total = [], 0, Decimal("0.00")
        for o in originals:
            ref = f"LAL-{o.pk}"
            if CurrentAccountMovement.objects.filter(book=ergene.book,
                                                     reference=ref).exists():
                w(f"  {ref:<10} already mirrored — skipped")
                skipped += 1
                continue
            amount = -(o.amount or Decimal("0"))
            base = -(o.amount_base or Decimal("0"))
            total += base
            doc = (o.reference or "").strip()
            text = (o.description or o.get_movement_type_display()).strip()
            description = f"Laleli: {doc} · {text}" if doc else f"Laleli: {text}"
            made.append((o, ref, amount, base, description[:255]))
            w(f"  {ref:<10} {o.date}  laleli {o.amount_base:>10} -> ergene {base:>10}")
            w(f"             {description[:88]!r}")

        if not made:
            w(self.style.NOTICE("\nAll four already mirrored — nothing to do."))
            return

        w(f"\n  net effect on Ergene: {total}")
        w(f"  Ergene {ergene.cached_balance} -> {ergene.cached_balance + total}")

        try:
            with transaction.atomic():
                for o, ref, amount, base, description in made:
                    CurrentAccountMovement.objects.create(
                        current_account=ergene, book=ergene.book, date=o.date,
                        movement_type="intercompany", amount=amount,
                        amount_base=base, currency=o.currency,
                        exchange_rate=o.exchange_rate, reference=ref,
                        description=description,
                    )
                ergene.recompute_balance(save=True)
                partner.refresh_from_db()
                ergene.refresh_from_db()
                w(f"\n  Ergene  {ergene.name[:26]:<26} {ergene.cached_balance:>12}")
                w(f"  Laleli  {partner.name[:26]:<26} {partner.cached_balance:>12}")
                drift = ergene.cached_balance + partner.cached_balance
                w(f"  sum (0.00 = exact mirror)  {drift:>17}")
                if drift:
                    w(self.style.WARNING(
                        "  NOT a mirror yet — the DAD merge into KARFF has not "
                        "been run, so Laleli is still missing the 739.89."))
                else:
                    w(self.style.SUCCESS("  exact mirror"))
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            w(self.style.NOTICE("\nDry run — nothing written. "
                                "Re-run with --apply."))
            return
        w(self.style.SUCCESS("\nCommitted."))
