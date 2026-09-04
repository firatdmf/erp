"""Find — and optionally merge — duplicate current accounts.

The DB constraints on CariAccount already stop the *same* CRM entity from
getting two accounts in one book. What they can't catch is one real-world
customer showing up twice behind different rows:

  * a Contact-linked account next to that contact's Company-linked account
    (get_or_create_cari_for_order prefers the company, but a direct call to
    get_or_create_cari_for_contact makes the contact one anyway),
  * two accounts carrying the same tax number (VKN),
  * two unlinked accounts typed in by hand under the same name.

Dry-run by default — it only prints what it found. Pass --apply to actually
merge, which re-points every row that references the duplicate (movements,
invoices, payments, checks, orders — discovered via Django's relation graph,
so new FKs are picked up automatically) onto the surviving account, then
deletes the duplicate.

    python manage.py dedupe_cari_accounts                  # report only
    python manage.py dedupe_cari_accounts --include-names  # + name matches
    python manage.py dedupe_cari_accounts --apply          # merge them
    python manage.py dedupe_cari_accounts --apply --deactivate  # keep the row

Some duplicates the rules cannot see, because the names differ by exactly
the thing that makes them separate rows — a customer the legacy ledger
split per year ("ÖZCAN ŞAHSİ 2024/2025/2026") or per shipment. Name those
groups yourself; the merge, the blockers and the dry run are the same:

    python manage.py dedupe_cari_accounts --book 2 \\
        --merge 88888,2025Ö --into 99999 --merge-cross-entity

NB: after a cross-entity merge the losing CRM records have no account
left, and any call to get_or_create_cari_for_* will mint them a fresh
one. Delete or merge those records too, or the duplicates grow back.
"""
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from accounting.models import CariAccount

# Turkish → ASCII, so "GÜMÜŞ TEKSTİL" and "GUMUS TEKSTIL" land in one group.
_TR = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})

# Legal-form noise that shouldn't decide whether two names are the same.
_SUFFIXES = {
    "ltd", "sti", "as", "a", "s", "san", "tic", "sanayi", "ticaret", "ve",
    "limited", "sirketi", "anonim", "ith", "ihr", "ithalat", "ihracat",
    "tekstil", "inc", "co", "llc", "gmbh",
}

# Which link makes an account the canonical one. Matches the resolution
# priority in services.get_or_create_cari_for_order (company wins).
_LINK_RANK = {"company": 3, "supplier": 2, "contact": 1, "": 0}

# Blank-only fields copied from the duplicate onto the survivor.
_FILL_FIELDS = [
    "tax_office", "tax_number", "identity_number", "billing_address",
    "billing_city", "email", "phone",
]


def _norm_name(value):
    """Squash a company name down to its identifying words."""
    text = (value or "").translate(_TR).lower()
    words = ["".join(ch for ch in w if ch.isalnum()) for w in text.split()]
    words = [w for w in words if w and w not in _SUFFIXES]
    return " ".join(words)


def _norm_tax(value):
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits if len(digits) >= 10 else ""


def _link_kind(cari):
    if cari.company_id:
        return "company"
    if cari.supplier_id:
        return "supplier"
    if cari.contact_id:
        return "contact"
    return ""


def _link_key(cari):
    """Identifies WHICH real entity an account points at."""
    kind = _link_kind(cari)
    if not kind:
        return None
    return (kind, getattr(cari, f"{kind}_id"))


class Command(BaseCommand):
    help = "Report (and optionally merge) duplicate current accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually merge. Without this the command only reports.",
        )
        parser.add_argument(
            "--book", type=int, default=None,
            help="Restrict to one book id (default: every book).",
        )
        parser.add_argument(
            "--include-names", action="store_true",
            help="Also group accounts by normalised name. Looser than the "
                 "link/tax rules — review the report before applying.",
        )
        parser.add_argument(
            "--deactivate", action="store_true",
            help="Set is_active=False on the merged-away account instead of "
                 "deleting it.",
        )
        parser.add_argument(
            "--merge-cross-entity", action="store_true",
            help="Also merge groups whose accounts point at DIFFERENT CRM "
                 "entities. Skipped by default: the losing entity would have "
                 "no account and the app would create a fresh one for it.",
        )
        parser.add_argument(
            "--allow-currency-mismatch", action="store_true",
            help="Merge even when the accounts use different currencies "
                 "(their balances stop being comparable).",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Process at most N duplicate groups.",
        )
        parser.add_argument(
            "--merge", default=None,
            help="Merge these account CODES (comma-separated) regardless of "
                 "what the detection rules think. For duplicates the rules "
                 "cannot see — a customer the legacy ledger split by year or "
                 "by shipment, where the names differ by exactly the thing "
                 "that makes them separate rows.",
        )
        parser.add_argument(
            "--into", default=None,
            help="The account CODE that survives a --merge. Required with it: "
                 "when a human names the group, a human names the keeper, "
                 "rather than the ranking picking one of three plausible rows.",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **opts):
        self.apply = opts["apply"]
        self.deactivate = opts["deactivate"]
        self.cross_entity = opts["merge_cross_entity"]
        self.allow_currency = opts["allow_currency_mismatch"]

        qs = CariAccount.objects.select_related(
            "book", "contact", "contact__company", "company", "supplier",
            "default_currency",
        ).annotate(n_moves=Count("movements"))
        if opts["book"]:
            qs = qs.filter(book_id=opts["book"])

        accounts = list(qs)
        if not accounts:
            self.stdout.write("No current accounts found.")
            return

        if opts["merge"] or opts["into"]:
            groups = [self._explicit_group(accounts, opts)]
        else:
            groups = self._find_groups(accounts, opts["include_names"])
        if opts["limit"]:
            groups = groups[: opts["limit"]]

        if not groups:
            self.stdout.write(self.style.SUCCESS(
                f"Checked {len(accounts)} accounts — no duplicates found."))
            return

        header = "Merging" if self.apply else "Found"
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"{header} {len(groups)} duplicate group(s) "
            f"across {len(accounts)} accounts:\n"))

        merged = skipped = 0
        for group in groups:
            if self._handle_group(group):
                merged += 1
            else:
                skipped += 1

        self.stdout.write("")
        if self.apply:
            self.stdout.write(self.style.SUCCESS(
                f"Merged {merged} group(s); skipped {skipped}."))
            self.stdout.write(
                "Note: nothing stops these from coming back — the code path "
                "that creates a contact-level account for a contact who "
                "belongs to a company is unchanged.")
        else:
            self.stdout.write(self.style.WARNING(
                f"Dry run — nothing changed. {merged} group(s) would be "
                f"merged, {skipped} need attention. Re-run with --apply."))

    # ------------------------------------------------------------------
    def _find_groups(self, accounts, include_names):
        """Bucket accounts by each rule, then union overlapping buckets so a
        customer caught by two rules is reported once."""
        buckets = defaultdict(list)  # key -> [account]
        by_pk = {a.pk: a for a in accounts}

        # Rule 1 — contact-linked account vs its company's account.
        company_owner = {}
        for a in accounts:
            if a.company_id:
                company_owner[(a.book_id, a.company_id)] = a
        for a in accounts:
            company_id = getattr(a.contact, "company_id", None) if a.contact_id else None
            owner = company_owner.get((a.book_id, company_id)) if company_id else None
            if owner and owner.pk != a.pk:
                key = ("link", a.book_id, company_id)
                buckets[key].extend([owner, a])

        # Rule 2 — same tax number.
        for a in accounts:
            tax = _norm_tax(a.tax_number)
            if tax:
                buckets[("tax", a.book_id, tax)].append(a)

        # Rule 3 — same normalised name (opt-in).
        if include_names:
            for a in accounts:
                name = _norm_name(a.name)
                if name:
                    buckets[("name", a.book_id, name)].append(a)

        # Union buckets that share an account (disjoint-set over pks).
        parent = {a.pk: a.pk for a in accounts}

        def find(pk):
            while parent[pk] != pk:
                parent[pk] = parent[parent[pk]]
                pk = parent[pk]
            return pk

        def union(a_pk, b_pk):
            ra, rb = find(a_pk), find(b_pk)
            if ra != rb:
                parent[rb] = ra

        reasons = defaultdict(set)
        for key, members in buckets.items():
            pks = {m.pk for m in members}
            if len(pks) < 2:
                continue
            first = min(pks)
            for pk in pks:
                union(first, pk)
                reasons[pk].add(key[0])

        clusters = defaultdict(list)
        for pk in parent:
            if pk in reasons:
                clusters[find(pk)].append(by_pk[pk])

        out = []
        for members in clusters.values():
            if len(members) < 2:
                continue
            why = sorted({r for m in members for r in reasons[m.pk]})
            out.append((members, why))
        out.sort(key=lambda g: (-len(g[0]), g[0][0].pk))
        return out

    # ------------------------------------------------------------------
    def _explicit_group(self, accounts, opts):
        """Build the one group the operator named on the command line.

        Codes are per-book, so an ambiguous one is an error rather than a
        guess — merging the wrong book's account is not something to
        discover afterwards.
        """
        if not (opts["merge"] and opts["into"]):
            raise CommandError("--merge and --into are used together.")

        wanted = [c.strip() for c in opts["merge"].split(",") if c.strip()]
        keeper = opts["into"].strip()
        by_code = defaultdict(list)
        for a in accounts:
            by_code[a.code].append(a)

        def one(code):
            found = by_code.get(code) or []
            if not found:
                raise CommandError(
                    f"No account with code {code!r}"
                    + (f" in book {opts['book']}" if opts["book"] else "")
                )
            if len(found) > 1:
                books = ", ".join(f"{a.book_id}:{a.book.name}" for a in found)
                raise CommandError(
                    f"Code {code!r} exists in several books ({books}) — "
                    "pass --book to say which."
                )
            return found[0]

        survivor = one(keeper)
        losers = [one(c) for c in wanted if c != keeper]
        if not losers:
            raise CommandError("--merge named nothing that --into does not.")
        books = {a.book_id for a in [survivor] + losers}
        if len(books) > 1:
            raise CommandError(
                "These accounts are in different books. A book is a separate "
                "business and its balances are its own — merging across one "
                "would move money between them."
            )
        self._forced_survivor = survivor
        return ([survivor] + losers, ["named on the command line"])

    # ------------------------------------------------------------------
    def _rank(self, cari):
        """Higher is more likely to be the keeper."""
        return (
            _LINK_RANK[_link_kind(cari)],
            getattr(cari, "n_moves", 0),
            -cari.created_at.timestamp() if cari.created_at else 0,
            -cari.pk,
        )

    def _describe(self, cari, tag=""):
        kind = _link_kind(cari) or "unlinked"
        link = ""
        if kind != "unlinked":
            link = f" → {kind} #{getattr(cari, kind + '_id')}"
        return (f"    {tag:<6} [{cari.pk}] {cari.code} | {cari.name}{link} | "
                f"{getattr(cari, 'n_moves', 0)} movement(s) | "
                f"balance {cari.cached_balance} "
                f"{cari.default_currency.code if cari.default_currency_id else ''}")

    def _handle_group(self, group):
        members, why = group
        forced = getattr(self, "_forced_survivor", None)
        if forced is not None:
            survivor = forced
            losers = [m for m in members if m.pk != forced.pk]
        else:
            members = sorted(members, key=self._rank, reverse=True)
            survivor, losers = members[0], members[1:]

        self.stdout.write(f"  book #{survivor.book_id} — matched by {', '.join(why)}")
        self.stdout.write(self._describe(survivor, "KEEP"))
        for loser in losers:
            self.stdout.write(self._describe(loser, "MERGE"))

        skip = self._blockers(survivor, losers)
        if skip:
            self.stdout.write(self.style.WARNING(f"    SKIPPED: {skip}\n"))
            return False

        if not self.apply:
            self.stdout.write("")
            return True

        with transaction.atomic():
            for loser in losers:
                self._merge(survivor, loser)
            survivor.save()
            survivor.recompute_balance()
        self.stdout.write("")
        return True

    def _blockers(self, survivor, losers):
        """Reasons this group shouldn't be merged automatically."""
        keys = {_link_key(a) for a in [survivor] + losers}
        keys.discard(None)
        kinds = {k[0] for k in keys}
        # Contact + its own company is the expected shape — not cross-entity.
        cross = len(keys) > 1 and kinds != {"contact", "company"}
        if cross and not self.cross_entity:
            return ("accounts point at different CRM entities "
                    f"({sorted(keys)}) — pass --merge-cross-entity to force")

        currencies = {a.default_currency_id for a in [survivor] + losers}
        if len(currencies) > 1 and not self.allow_currency:
            return ("different currencies — pass --allow-currency-mismatch "
                    "to force")
        return None

    def _merge(self, survivor, loser):
        """Re-point everything that references `loser` at `survivor`."""
        for rel in CariAccount._meta.related_objects:
            model, field = rel.related_model, rel.field.name
            if rel.many_to_many:
                raise CommandError(
                    f"{model._meta.label}.{field} is many-to-many — this "
                    "command doesn't know how to move those rows.")
            moved = model._base_manager.filter(**{field: loser}).update(
                **{field: survivor})
            if moved:
                self.stdout.write(
                    f"      moved {moved} × {model._meta.label}.{field}")

        # Carry over anything the survivor is missing.
        for name in _FILL_FIELDS:
            if not getattr(survivor, name, "") and getattr(loser, name, ""):
                setattr(survivor, name, getattr(loser, name))
                self.stdout.write(f"      filled {name} from [{loser.pk}]")

        # A customer account merged with a supplier account is both.
        if survivor.type != loser.type and {survivor.type, loser.type} <= {"customer", "supplier"}:
            survivor.type = "both"
            self.stdout.write("      type → both")

        # Opening balances are real money — drop one and the ledger is wrong.
        if loser.opening_balance:
            survivor.opening_balance = (
                (survivor.opening_balance or Decimal("0.00")) + loser.opening_balance)
            survivor.opening_balance_date = (
                survivor.opening_balance_date or loser.opening_balance_date)
            self.stdout.write(
                f"      opening_balance += {loser.opening_balance} "
                f"→ {survivor.opening_balance}")

        stamp = timezone.now().date().isoformat()
        note = f"[{stamp}] Merged duplicate {loser.code} ({loser.name})."
        if loser.notes.strip():
            note += f" Its notes: {loser.notes.strip()}"
        survivor.notes = f"{survivor.notes.rstrip()}\n{note}".strip()

        if self.deactivate:
            loser.is_active = False
            loser.notes = (f"{loser.notes.rstrip()}\n[{stamp}] Merged into "
                           f"{survivor.code} (#{survivor.pk}).").strip()
            loser.save(update_fields=["is_active", "notes", "updated_at"])
            self.stdout.write(f"      deactivated [{loser.pk}] {loser.code}")
        else:
            loser.delete()  # PROTECT FKs make this fail loudly if we missed any
            self.stdout.write(f"      deleted [{loser.pk}] {loser.code}")
