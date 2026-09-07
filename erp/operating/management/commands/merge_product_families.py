# -*- coding: utf-8 -*-
"""Fold split catalog product families back into one product.

The same fabric was sitting under two Product rows: a real, featured web
product carrying the images and the description, and a hidden husk that
the warehouse sync had minted under the *correct* code. K24592's nine
colours were split four/five across "24592" and "K24592"; ŞANTUK was
spelled "Santuk" on the featured row; the MRK00xx series was split
between "5019" and "MT-5019".

Because Product.sku is globally unique, renaming alone cannot fix this —
the hidden row already owns the code the featured row should have. So the
two rows are MERGED, and these are the five that were decided by hand:

    featured row            absorbs         becomes
    "24592"      (#220)     "K24592"        K24592
    "Santuk"     (#196)     "ŞANTUK"        ŞANTUK
    "5019"       (#227)     "MT-5019"       MT-5019
    "K25289"     (#167)     "K25289İ"       K25289İ
    "Liva"       (#199)     "Liva" (#740)   Liva

The FEATURED row always survives: it is the one holding the ProductFiles,
the attributes and the bill of materials (26 files on #220 alone), and it
is what the storefront links to. The hidden row hands over its variants
and anything else pointing at it, then goes.

Nothing is deleted that still holds stock: a variant moves house, keeping
its id, so warehouse rows and order lines follow it untouched.

Dry run by default; --apply commits. Idempotent — a family already merged
reports "already merged" and is skipped.

    python manage.py merge_product_families
    python manage.py merge_product_families --apply
"""
from django.core.management.base import BaseCommand
from django.db import transaction

# (survivor sku, absorbed sku, new title, new sku). Products are found by
# their CURRENT sku, which is unique; the pk in the comment is what it was
# when the merge was decided, recorded so a mismatch is obvious.
MERGES = [
    ("24592",     "K24592",  "K24592",  "K24592"),   # #220 absorbs #360
    ("KZL000131", "ŞANTUK",  "ŞANTUK",  "ŞANTUK"),   # #196 absorbs #759
    ("5019",      "MT-5019", "MT-5019", "MT-5019"),  # #227 absorbs #1090
    ("K25289",    "K25289İ", "K25289İ", "K25289İ"),  # #167 absorbs #425
    ("2047",      "Liva",    "Liva",    "Liva"),     # #199 absorbs #740
]


class Command(BaseCommand):
    help = ("Merge the five split catalog product families into one product "
            "each, keeping the featured row. Dry run unless --apply.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")

    def handle(self, *args, **opts):
        from marketing.models import Product

        w = self.stdout.write
        apply = opts["apply"]
        merged = skipped = 0

        for surv_sku, absorb_sku, new_title, new_sku in MERGES:
            survivor = Product.objects.filter(sku=surv_sku).first()
            absorbed = Product.objects.filter(sku=absorb_sku).first()

            # Idempotence, checked FIRST: once merged the survivor carries
            # the new sku, so a second run looks up the same row as both
            # sides of the merge. That is "done", not "same row, confused".
            if survivor is None:
                done = Product.objects.filter(sku=new_sku, title=new_title).first()
                if done is not None and (absorbed is None or absorbed.pk == done.pk):
                    w(f"  {new_sku}: already merged (#{done.pk})")
                    skipped += 1
                    continue

            if survivor is None:
                # The survivor may already have been renamed by a half-run.
                survivor = Product.objects.filter(sku=new_sku).first()
            if survivor is None:
                w(self.style.WARNING(
                    f"  {new_sku}: no survivor found (looked for sku "
                    f"{surv_sku!r} then {new_sku!r}) — skipped"))
                skipped += 1
                continue
            if absorbed is None:
                if survivor.sku == new_sku and survivor.title == new_title:
                    w(f"  {new_sku}: already merged (#{survivor.pk})")
                else:
                    w(self.style.WARNING(
                        f"  {new_sku}: nothing left to absorb (sku {absorb_sku!r} "
                        f"not found) — renaming survivor only"))
                    self._rename(survivor, new_title, new_sku, apply, w)
                skipped += 1
                continue
            if survivor.pk == absorbed.pk:
                w(f"  {new_sku}: survivor and absorbed are the same row — skipped")
                skipped += 1
                continue

            w(f"  {survivor.title!r} (#{survivor.pk}, featured={survivor.featured}) "
              f"absorbs {absorbed.title!r} (#{absorbed.pk})")

            moved = self._move_dependents(survivor, absorbed, apply, w)
            w(f"      moved: {moved or 'nothing'}")

            if apply:
                with transaction.atomic():
                    # Free the code BEFORE the survivor claims it: Product.sku
                    # is globally unique, so the husk must let go first.
                    absorbed.delete()
                    self._rename(survivor, new_title, new_sku, apply, w)
            else:
                w(f"      DELETE '{absorbed.title}' (#{absorbed.pk})")
                self._rename(survivor, new_title, new_sku, apply, w)
            merged += 1

        w("")
        w(f"  families merged  {merged:>4}")
        w(f"  skipped          {skipped:>4}")
        w("")
        if apply:
            w(self.style.SUCCESS("Applied."))
        else:
            w(self.style.WARNING(
                "DRY RUN — nothing was written. Re-run with --apply."))

    def _rename(self, survivor, new_title, new_sku, apply, w):
        if survivor.title == new_title and survivor.sku == new_sku:
            return
        w(f"      RENAME #{survivor.pk}: title {survivor.title!r} -> {new_title!r}, "
          f"sku {survivor.sku!r} -> {new_sku!r}")
        if apply:
            survivor.title = new_title
            survivor.sku = new_sku
            survivor.save(update_fields=["title", "sku"])

    def _move_dependents(self, survivor, absorbed, apply, w):
        """Repoint everything that references the absorbed product.

        OrderItem.product is PROTECT, so a single order line left behind
        would abort the delete — and an InvoiceItem or PurchaseRequestItem
        would silently become NULL instead, quietly losing which product a
        line was for. Both are moved rather than left to on_delete.
        """
        from marketing.models import Product

        moved = []
        for f in Product._meta.get_fields():
            if not (f.auto_created and not f.concrete):
                continue
            rel = f.field
            qs = rel.model.objects.filter(**{rel.name: absorbed})
            n = qs.count()
            if not n:
                continue
            moved.append(f"{rel.model.__name__}.{rel.name}={n}")
            if apply:
                qs.update(**{rel.name: survivor})
        return ", ".join(moved)
