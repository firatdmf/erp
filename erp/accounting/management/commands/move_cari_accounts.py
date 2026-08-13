"""Move current accounts into another book.

The project is consolidating onto a single book. An account's book is not just
a column on the account: its movements, invoices, payments and checks each
carry their own book, and the book takes part in four unique constraints —

    (book, code)             on CariAccount
    (book, contact/company/supplier)  one account per book per CRM entity
    (book, series, number)   on Invoice
    (book, number)           on Payment

so a move that only updates the account leaves the ledger inconsistent, and one
that ignores the constraints fails halfway. Everything is checked up front and
written in a single transaction.

Two things this handles that are easy to miss:

* Each book ran its own CARI-nnn sequence from 001, so unrelated accounts in
  different books share codes. The code is a label, not a key — invoices,
  payments and movements all reference the account by id — so an incoming
  account whose code is taken is renumbered rather than refused.

* The destination's own sequence has to be advanced past whatever arrived.
  Book 2 sat at next_cari_seq=3 while accounts numbered up to CARI-074 moved
  in; left alone it would have handed out CARI-003 and eventually collided
  with them.

    python manage.py move_cari_accounts --to 2 --suppliers
    python manage.py move_cari_accounts --to 2 --from-book 1 --apply
    python manage.py move_cari_accounts --to 2 --ids 3,25,26 --apply
"""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import (
    CariAccount, CariMovement, CariSettings, CheckOrPromissoryNote, Invoice,
    Payment,
)

# Models holding both a cari FK and their own book column.
CARRIERS = [CariMovement, Invoice, Payment, CheckOrPromissoryNote]


class Command(BaseCommand):
    help = "Move current accounts (and everything they own) into another book."

    def add_arguments(self, parser):
        parser.add_argument("--to", type=int, required=True,
                            help="Destination book id.")
        parser.add_argument("--ids", default="",
                            help="Comma-separated account ids to move.")
        parser.add_argument("--from-book", type=int, default=None,
                            help="Move every account in this book.")
        parser.add_argument("--suppliers", action="store_true",
                            help="Move accounts linked to a supplier record, "
                                 "or typed supplier/both.")
        parser.add_argument("--apply", action="store_true",
                            help="Actually write. Without this it only reports.")

    # ------------------------------------------------------------------
    def handle(self, *args, **o):
        target = o["to"]
        if not CariAccount.objects.model.book.field.related_model.objects.filter(
                pk=target).exists():
            raise CommandError(f"Book {target} does not exist.")

        qs = CariAccount.objects.none()
        if o["ids"]:
            ids = [int(x) for x in o["ids"].split(",") if x.strip()]
            qs = qs | CariAccount.objects.filter(pk__in=ids)
        if o["from_book"] is not None:
            qs = qs | CariAccount.objects.filter(book_id=o["from_book"])
        if o["suppliers"]:
            qs = (qs | CariAccount.objects.filter(supplier__isnull=False)
                  | CariAccount.objects.filter(type__in=["supplier", "both"]))
        if not (o["ids"] or o["from_book"] is not None or o["suppliers"]):
            raise CommandError("Give --ids, --from-book or --suppliers.")

        accounts = list(qs.exclude(book_id=target).distinct()
                        .select_related("book").order_by("id"))
        if not accounts:
            self.stdout.write("Nothing to move.")
            return

        problems, recode = [], {}
        renum_inv, renum_pay = [], []
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Moving {len(accounts)} account(s) into book {target}"))

        for a in accounts:
            owned = {m.__name__: m.objects.filter(cari=a).count()
                     for m in CARRIERS}
            owned = {k: v for k, v in owned.items() if v}
            self.stdout.write(
                f"  [{a.id:>4}] book{a.book_id} {a.code:10} {a.name[:28]:30} "
                f"bal={a.cached_balance:>11,.2f} active={a.is_active}  "
                f"{owned or ''}")

            twin = (CariAccount.objects.filter(book_id=target, code=a.code)
                    .exclude(pk=a.pk).first())
            if twin:
                recode[a.id] = twin
                self.stdout.write(
                    f"         code {a.code} held in book {target} by "
                    f"#{twin.id} ({twin.name[:26]}) — will renumber")

            for field in ("contact_id", "company_id", "supplier_id"):
                val = getattr(a, field)
                if val and (CariAccount.objects
                            .filter(book_id=target, **{field: val})
                            .exclude(pk=a.pk).exists()):
                    problems.append(
                        f"#{a.id} {a.name[:24]}: {field}={val} already has an "
                        f"account in book {target} — merge them first")

            # Invoice and payment numbers collide for the same reason account
            # codes do — each book ran its own sequence — so they are
            # renumbered rather than refused. These are user-facing document
            # numbers, so every change is printed before anything is written.
            for inv in Invoice.objects.filter(cari=a):
                if (Invoice.objects
                        .filter(book_id=target, series=inv.series,
                                number=inv.number)
                        .exclude(pk=inv.pk).exists()):
                    renum_inv.append(inv)
            for pay in Payment.objects.filter(cari=a):
                if (Payment.objects.filter(book_id=target, number=pay.number)
                        .exclude(pk=pay.pk).exists()):
                    renum_pay.append(pay)

        if problems:
            self.stdout.write(self.style.ERROR("\nABORT — collisions:"))
            for p in problems:
                self.stdout.write(f"  * {p}")
            raise CommandError("Nothing was written.")

        new_code = self._allocate_codes(target, accounts, recode)
        if new_code:
            self.stdout.write("\nrenumbering on arrival:")
            for aid, code in new_code.items():
                old = next(a for a in accounts if a.id == aid)
                self.stdout.write(f"  [{aid}] {old.name[:30]:32} "
                                  f"{old.code} -> {code}")

        new_inv, new_pay = self._allocate_docs(target, renum_inv, renum_pay)
        for doc, mapping, label in ((renum_inv, new_inv, "invoice"),
                                    (renum_pay, new_pay, "payment")):
            if doc:
                self.stdout.write(f"\nrenumbering {label}s (number taken in "
                                  f"book {target}):")
                for d in doc:
                    self.stdout.write(
                        f"  {d.number} -> {mapping[d.pk]}   "
                        f"{d.cari.name[:26]:28} {d.total if label == 'invoice' else d.amount:>10,.2f}")

        settings_obj = CariSettings.objects.filter(book_id=target).first()
        need = self._next_seq(target, accounts, new_code)
        need_inv, need_pay = self._next_doc_seqs(target, renum_inv, renum_pay,
                                                 new_inv, new_pay)
        if settings_obj:
            bumps = []
            if settings_obj.next_cari_seq < need:
                bumps.append(f"next_cari_seq {settings_obj.next_cari_seq} -> {need}")
            if settings_obj.next_invoice_seq < need_inv:
                bumps.append(f"next_invoice_seq {settings_obj.next_invoice_seq} -> {need_inv}")
            if settings_obj.next_payment_seq < need_pay:
                bumps.append(f"next_payment_seq {settings_obj.next_payment_seq} -> {need_pay}")
            if bumps:
                self.stdout.write(f"\nbook {target} counters — the destination's "
                                  f"own sequences sit below the numbers arriving,\n"
                                  f"  so without this it would later reissue one "
                                  f"that already exists:")
                for b in bumps:
                    self.stdout.write(f"    {b}")

        if not o["apply"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — nothing written. Re-run with --apply."))
            return

        with transaction.atomic():
            # Renumber BEFORE moving. Changing a document's book is what
            # triggers the (book, number) constraint, so a document still
            # carrying a number the destination owns fails on the way in.
            for inv in renum_inv:
                Invoice.objects.filter(pk=inv.pk).update(number=new_inv[inv.pk])
            for pay in renum_pay:
                Payment.objects.filter(pk=pay.pk).update(number=new_pay[pay.pk])
            for a in accounts:
                for model in CARRIERS:
                    model.objects.filter(cari=a).update(book_id=target)
                upd = {"book_id": target}
                if a.id in new_code:
                    upd["code"] = new_code[a.id]
                CariAccount.objects.filter(pk=a.pk).update(**upd)
            if settings_obj:
                CariSettings.objects.filter(pk=settings_obj.pk).update(
                    next_cari_seq=max(settings_obj.next_cari_seq, need),
                    next_invoice_seq=max(settings_obj.next_invoice_seq, need_inv),
                    next_payment_seq=max(settings_obj.next_payment_seq, need_pay),
                )
            for a in accounts:
                CariAccount.objects.get(pk=a.pk).recompute_balance(save=True)

        self.stdout.write(self.style.SUCCESS(f"\nMoved {len(accounts)} account(s)."))
        stray = sum(m.objects.filter(cari__book_id=target)
                    .exclude(book_id=target).count() for m in CARRIERS)
        self.stdout.write(f"  rows in book {target} whose own book disagrees: {stray}")

    # ------------------------------------------------------------------
    def _allocate_codes(self, target, accounts, recode):
        """Fresh codes for arrivals whose own code is taken in the target."""
        taken = set(CariAccount.objects.filter(book_id=target)
                    .values_list("code", flat=True))
        taken |= {a.code for a in accounts if a.id not in recode}
        out, n = {}, 0
        for aid in recode:
            while True:
                n += 1
                cand = f"CARI-{n:03d}"
                if cand not in taken:
                    break
            taken.add(cand)
            out[aid] = cand
        return out

    def _next_seq(self, target, accounts, new_code):
        """One past the highest CARI-nnn that will exist in the target book."""
        codes = set(CariAccount.objects.filter(book_id=target)
                    .values_list("code", flat=True))
        codes |= {new_code.get(a.id, a.code) for a in accounts}
        highest = 0
        for code in codes:
            m = re.fullmatch(r"CARI-0*(\d+)", (code or "").strip(), re.I)
            if m:
                highest = max(highest, int(m.group(1)))
        return highest + 1

    # ------------------------------------------------------------------
    def _allocate_docs(self, target, invoices, payments):
        """Fresh document numbers, keeping each document's own prefix/year.

        Numbers look like TAH-2026-000007 or FAT-2026-000060 — prefix, year,
        then a per-book sequence. Only the sequence part is reassigned, so a
        renumbered document keeps its type and year and stays recognisable.
        """
        # Numbers must be free in EVERY book, not just the destination. A
        # replacement is written while the document still sits in its old book
        # — picking one that is merely unused in the target collides with the
        # source instead, and the whole move rolls back.
        inv_taken = set(Invoice.objects.values_list("series", "number"))
        pay_taken = set(Payment.objects.values_list("number", flat=True))
        new_inv, new_pay = {}, {}

        for inv in invoices:
            new_inv[inv.pk] = self._free_number(
                inv.number, lambda n: (inv.series, n) in inv_taken)
            inv_taken.add((inv.series, new_inv[inv.pk]))
        for pay in payments:
            new_pay[pay.pk] = self._free_number(
                pay.number, lambda n: n in pay_taken)
            pay_taken.add(new_pay[pay.pk])
        return new_inv, new_pay

    @staticmethod
    def _free_number(number, is_taken):
        """Next unused number sharing this one's prefix and year."""
        m = re.fullmatch(r"(.+?-\d{4}-)(\d+)", (number or "").strip())
        if not m:
            # Unrecognised shape — suffix rather than risk mangling it.
            cand, n = f"{number}-B", 1
            while is_taken(cand):
                n += 1
                cand = f"{number}-B{n}"
            return cand
        head, width = m.group(1), len(m.group(2))
        seq = int(m.group(2))
        while True:
            seq += 1
            cand = f"{head}{str(seq).zfill(width)}"
            if not is_taken(cand):
                return cand

    def _next_doc_seqs(self, target, renum_inv, renum_pay, new_inv, new_pay):
        """One past the highest sequence each document series will hold."""
        def highest(values):
            best = 0
            for v in values:
                m = re.fullmatch(r".+?-\d{4}-(\d+)", (v or "").strip())
                if m:
                    best = max(best, int(m.group(1)))
            return best

        inv_nums = set(Invoice.objects.filter(book_id=target)
                       .values_list("number", flat=True)) | set(new_inv.values())
        pay_nums = set(Payment.objects.filter(book_id=target)
                       .values_list("number", flat=True)) | set(new_pay.values())
        # Documents arriving with the accounts count too.
        inv_nums |= {i.number for i in renum_inv}
        pay_nums |= {p.number for p in renum_pay}
        return highest(inv_nums) + 1, highest(pay_nums) + 1
