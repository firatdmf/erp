"""
Merge duplicate CRM contacts.

`Contact.name` is not unique, so the same person can end up in the CRM
twice — usually once under a Latin spelling and once under a Turkish one
("Tatyana Warsaw" / "TATYANA VARŞOVA"). The two halves tend to carry
different things: the ledger link sits on one, the phone number and notes
on the other.

This moves everything the duplicate owns onto the survivor, fills in any
field the survivor left blank, and deletes the duplicate. Ledger accounts
are re-pointed, never combined — one client with an account in two books
keeps two accounts.

Dry run by default; pass --apply to commit.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models_accounts import CariAccount
from crm.models import Contact, Note, Supplier

# Single-valued fields the survivor adopts only where it has nothing of
# its own. `name` is deliberately absent — pass --name to change it.
FILL_FIELDS = ("company_id", "job_title", "backgroundInfo", "address",
               "country", "birthday", "group_id")
# ArrayFields, merged as a union rather than overwritten.
LIST_FIELDS = ("email", "phone")


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Merge duplicate CRM contacts into a survivor."

    def add_arguments(self, parser):
        parser.add_argument("--survivor", type=int, required=True,
                            help="Contact id to keep")
        parser.add_argument("--duplicate", type=int, nargs="+", required=True,
                            help="Contact id(s) to fold in and delete")
        parser.add_argument("--name", default=None,
                            help="Rename the survivor (e.g. to the better spelling)")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self._run(options)
                if not options["apply"]:
                    raise _DryRun
        except _DryRun:
            self.stdout.write(self.style.WARNING(
                "\nDry run — rolled back. Re-run with --apply to commit."))

    def _run(self, options):
        try:
            survivor = Contact.objects.get(pk=options["survivor"])
        except Contact.DoesNotExist:
            raise CommandError(f"No contact #{options['survivor']}")
        if options["survivor"] in options["duplicate"]:
            raise CommandError("A contact cannot be its own duplicate")

        self.stdout.write(f"survivor: #{survivor.pk} {survivor.name!r}")

        for dup_id in options["duplicate"]:
            try:
                dup = Contact.objects.get(pk=dup_id)
            except Contact.DoesNotExist:
                raise CommandError(f"No contact #{dup_id}")

            # One contact may hold only one account per book, so a genuine
            # clash here means these are not the same person after all.
            survivor_books = set(
                CariAccount.objects.filter(contact=survivor).values_list("book_id", flat=True))
            clashes = CariAccount.objects.filter(
                contact=dup, book_id__in=survivor_books)
            if clashes.exists():
                raise CommandError(
                    f"#{dup_id} and #{survivor.pk} both hold an account in book(s) "
                    f"{sorted(set(clashes.values_list('book_id', flat=True)))} — "
                    f"merge those accounts first, or they are different people."
                )

            moved_accounts = CariAccount.objects.filter(contact=dup).update(contact=survivor)
            moved_notes = Note.objects.filter(contact=dup).update(contact=survivor)
            moved_suppliers = Supplier.objects.filter(
                linked_contact=dup).update(linked_contact=survivor)

            filled = []
            for field in FILL_FIELDS:
                if not getattr(survivor, field) and getattr(dup, field):
                    setattr(survivor, field, getattr(dup, field))
                    filled.append(field)
            for field in LIST_FIELDS:
                merged = list(getattr(survivor, field) or [])
                for value in getattr(dup, field) or []:
                    if value not in merged:
                        merged.append(value)
                        filled.append(field)
                setattr(survivor, field, merged)

            self.stdout.write(
                f"  #{dup.pk} {dup.name!r}: accounts {moved_accounts}, notes {moved_notes}, "
                f"suppliers {moved_suppliers}, adopted {sorted(set(filled)) or 'nothing'}"
            )
            dup.delete()

        if options["name"] and options["name"] != survivor.name:
            self.stdout.write(f"  rename {survivor.name!r} -> {options['name']!r}")
            survivor.name = options["name"]

        survivor.save()
        self.stdout.write(self.style.SUCCESS(
            f"\n#{survivor.pk} {survivor.name!r} | country={survivor.country!r} "
            f"email={survivor.email} phone={survivor.phone} | "
            f"accounts: {[a.code for a in survivor.cari_accounts.all()]}"
        ))
