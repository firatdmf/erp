"""Compose decomposed text already stored in the database.

macOS reports filenames in NFD — "HACİM" as H, A, C, I, U+0307, M — and an
importer that reads a name from a filename and writes it straight out
stores that decomposed form. It looks identical in every UI and is
invisible in a diff, but Postgres compares bytes: the browser sends the
composed form, so `name__icontains="HACİM"` never matches and the record
becomes unreachable by search.

This walks the text fields most likely to have come in from a file and
rewrites any that are not already NFC. Composing is safe and idempotent —
NFC is what everything else in the database already holds, and a string
that is already composed is left untouched.

Dry run by default; pass --apply to commit.
"""
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

# (app_label.Model, [text fields to compose])
TARGETS = [
    ("accounting.CariAccount", ["name", "notes", "billing_address", "billing_city"]),
    ("accounting.CariMovement", ["description", "reference"]),
    ("crm.Contact", ["name", "address", "backgroundInfo"]),
    ("crm.Company", ["name", "address", "backgroundInfo"]),
    ("crm.Supplier", ["company_name", "contact_name", "address"]),
]


class Command(BaseCommand):
    help = "Rewrite NFD-decomposed text as NFC so search can find it."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it nothing is written.")
        parser.add_argument("--show", type=int, default=8,
                            help="How many examples to print per model.")

    def handle(self, *args, **options):
        from django.apps import apps

        total = 0
        with transaction.atomic():
            for label, fields in TARGETS:
                model = apps.get_model(label)
                touched, shown = 0, 0
                for obj in model.objects.all().iterator():
                    dirty = []
                    for f in fields:
                        old = getattr(obj, f, None)
                        if not old or not isinstance(old, str):
                            continue
                        new = unicodedata.normalize("NFC", old)
                        if new != old:
                            setattr(obj, f, new)
                            dirty.append(f)
                    if not dirty:
                        continue
                    touched += 1
                    if shown < options["show"]:
                        shown += 1
                        self.stdout.write("    #{} {} {!r}".format(
                            obj.pk, ",".join(dirty), getattr(obj, dirty[0])[:44]))
                    if options["apply"]:
                        # update_fields keeps this off every other column and
                        # away from auto_now stamps on rows we are only
                        # re-encoding, not editing.
                        obj.save(update_fields=dirty)
                total += touched
                self.stdout.write("{:<26} {} row(s) to compose".format(label, touched))
            if not options["apply"]:
                transaction.set_rollback(True)

        self.stdout.write("")
        if options["apply"]:
            self.stdout.write(self.style.SUCCESS(f"composed {total} row(s)"))
        else:
            self.stdout.write(self.style.WARNING(
                f"dry run — {total} row(s) would change. Re-run with --apply."))
