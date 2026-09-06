"""
Clear the roll label-photo paths whose files are gone.

`WarehouseProductRoll.source_image` used to be written to MEDIA_ROOT, which
on this deployment is a container path with no volume mounted — so every
deploy wiped the photos while the database kept pointing at them. The column
then claims audit evidence that cannot be produced, which is worse than
claiming nothing.

This checks each path and clears ONLY the ones that genuinely do not
resolve. It has to run WHERE THE FILES WOULD BE — on the production host,
not a laptop — or it will report every photo as missing and, with --apply,
erase paths that were fine:

    railway ssh                     # or the Render shell
    python manage.py prune_missing_roll_images            # dry run
    python manage.py prune_missing_roll_images --apply

Rolls whose photo has moved to the CDN (`image_url`) are left alone; their
local path, if any, is a second copy and is checked the same way.

Dry run by default; pass --apply to commit.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from operating.models import WarehouseProductRoll


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = ("Clear WarehouseProductRoll.source_image where the file is gone. "
            "Must run on the host that holds MEDIA_ROOT.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")
        parser.add_argument("--warehouse", default=None,
                            help="Limit to one warehouse, by name.")
        parser.add_argument("--force-all", action="store_true",
                            dest="force_all",
                            help="Proceed even when EVERY path is missing — "
                                 "normally refused, since that is what "
                                 "running on the wrong host looks like.")

    def handle(self, *args, **opts):
        qs = (WarehouseProductRoll.objects
              .exclude(source_image="").exclude(source_image__isnull=True)
              .select_related("product", "product__warehouse"))
        if opts["warehouse"]:
            qs = qs.filter(product__warehouse__name=opts["warehouse"])

        root = str(settings.MEDIA_ROOT)
        self.stdout.write(f"MEDIA_ROOT: {root}")
        self.stdout.write(f"exists: {os.path.isdir(root)}")
        total = qs.count()
        self.stdout.write(f"rolls carrying a local photo path: {total}")
        if not total:
            return

        present, missing = [], []
        for roll in qs.iterator(chunk_size=500):
            path = os.path.join(root, roll.source_image.name.replace("/", os.sep))
            (present if os.path.exists(path) else missing).append(roll)

        self.stdout.write(f"  files present: {len(present)}")
        self.stdout.write(f"  files missing: {len(missing)}")
        on_cdn = sum(1 for r in missing if r.image_url)
        if on_cdn:
            self.stdout.write(f"  ...of which {on_cdn} already have a CDN copy, "
                              f"so only the dead local path is dropped")

        # A run that finds NOTHING is the signature of running in the wrong
        # place — an empty or absent MEDIA_ROOT looks exactly like a wiped
        # one. Refuse rather than clear every path in the database.
        if not present and missing and not opts["force_all"]:
            self.stdout.write(self.style.ERROR(
                "\nEvery single path is missing. That is exactly what running "
                "this on the wrong host looks like, so nothing was changed.\n"
                "Check MEDIA_ROOT above is the real one, and if the photos "
                "genuinely are all gone, re-run with --force-all."))
            return

        if not missing:
            self.stdout.write(self.style.SUCCESS("\nNothing to clear."))
            return

        try:
            with transaction.atomic():
                now = timezone.now()
                for roll in missing:
                    roll.source_image = None
                    note = (roll.notes or "").strip()
                    stamp = f"Label photo lost before {now:%Y-%m-%d} (local disk not persisted)"
                    roll.notes = f"{note} · {stamp}".strip(" ·")
                WarehouseProductRoll.objects.bulk_update(
                    missing, ["source_image", "notes"], batch_size=500)
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN — would clear {len(missing)} dead paths. "
                f"Re-run with --apply."))
            return
        self.stdout.write(self.style.SUCCESS(
            f"\nCleared {len(missing)} dead photo paths."))
