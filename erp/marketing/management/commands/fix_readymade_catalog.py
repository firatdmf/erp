"""
Bring the 13 ready-made curtain designs in line with the Karven spec sheet
before their stock is imported into the Ready-made Shop warehouse.

The spec — KarvenReadyMadeStock.xlsx — is the authority on which colourways
exist and what each one's EAN is. The catalog already agreed with it on 40 of
48 barcodes; this command closes the rest of the gap:

  1. Butterfly (RK24539) has `category = None`, which is why it never appears
     in the ready-made list even though it holds 149 sets. Categorise it.

  2. Dandelion's turquoise rod-pocket panel is in the spec (barcode
     712179795198) and 106 sets of it are on the floor, but the catalog only
     carries the four grommet variants. Create it.

  3. Every variant SKU becomes PARENT.SUFFIX — RK12471GW8 -> RK12471.GW8 —
     so the parent SKU is readable without knowing how long a design code is.
     Four RN1360 variants already have the dot; two Dandelion ones are
     lowercase (`rK72010GW8`) and get their capital back on the way through.

  4. Barcodes are backfilled from the spec where a variant has none.

The suffix is three characters and reads header / colour / length:

     R rod pocket   W Beyaz         8  84in (130 x 210 cm)
     G grommet      C Şampanya      9  95in (130 x 240 cm)
                    O Kirli Beyaz
                    I Fil Dişi
                    T Turkuaz, or Mavi & Şampanya on RN1360
                    M Mürdüm (RN1357), Konfeti (RN1381)
                    B Siyah & Krem (RN1370)

Most designs offer exactly ONE colourway per (design, header, length), which
is why the warehouse's own colour words are unreliable — a Peony box marked
KREM is Mürdüm, because Mürdüm is the only Peony there is. The stock importer
matches on design+header+length for that reason; this command only has to
make sure the variant those three point at actually exists and is named
consistently.

A NOTE ON ATTRIBUTES. ProductVariantAttribute.save() strips spaces from the
name and ProductVariantAttributeValue.save() replaces them with underscores,
but the rows in the database contain spaces ("size per panel", "130 x 210
cm") — they were written by something that bypassed save(). So a plain
get_or_create() here would not find the existing row and would then store a
mangled twin of it. Every attribute this command attaches is looked up and
reused; none is created.

Dry run by default; pass --apply to commit.

    python manage.py fix_readymade_catalog
    python manage.py fix_readymade_catalog --apply
"""
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marketing.models import (Product, ProductCategory, ProductVariant,
                              ProductVariantAttributeValue)

DEFAULT_SPEC = Path.home() / "Desktop" / "KarvenReadyMadeStock.xlsx"

CATEGORY = "ready-made_curtain"

# A ready-made parent SKU: R, an optional house letter, then the design code.
PARENT_RE = re.compile(r"^R[KN]?\d+$")

# Spec colourway -> the letter it occupies in a variant suffix. Two designs
# share T: Dandelion's Turkuaz and RN1360's Mavi & Şampanya. They are
# different colours but they never collide, because they are on different
# products and the letter is only ever read within one.
COLOUR_LETTER = {
    "Beyaz": "W",
    "Şampanya": "C",
    "Kirli Beyaz": "O",
    "Fil Dişi": "I",
    "Turkuaz": "T",
    "Mavi & Şampanya": "T",
    "Mürdüm (Altın & Mirle)": "M",
    "Konfeti": "M",
    "Siyah & Krem": "B",
}

# The one variant the catalog is genuinely missing. Its attributes are all
# reused from rows that already exist (see the note on save() above), except
# the colour: "turquoise" is created, and is safe to because it is a single
# word — save() only mangles values containing spaces. It is kept distinct
# from the existing "teal", which belongs to RN1360's Mavi & Şampanya.
NEW_VARIANT = {
    "parent": "RK72010",
    "suffix": "RT8",
    "barcode": "712179795198",
    "cost": Decimal("18.10"),
    "attributes": [("color", "turquoise"), ("size per panel", "130 x 210 cm"),
                   ("header", "rod pocket")],
}

# Confetti's 84cm panel records its width as 132 rather than 130 — the only
# variant in the catalog that does, and a typo rather than a real size. It is
# repointed at the existing "130 x 210 cm" row rather than having its own
# edited, which would rewrite the size for anything else pointing at it.
TYPO_FIX = ("RN1381", "RM8", "size per panel", "132 x 210 cm", "130 x 210 cm")

# Variants whose colour LETTER disagrees with the spec, as
# (parent, old suffix) -> (new suffix, old colour value, spec colour value).
# RN1360's grommet panel is catalogued white; the spec makes it Kirli Beyaz,
# which every other design writes as O. The warehouse calls it BEYAZ too, so
# this is the catalog choosing the spec's vocabulary over the shop floor's —
# deliberately, so that one letter means one colour across all 13 designs.
LETTER_FIX = {
    ("RN1360", "GW8"): ("GO8", "white", "off-white"),
    ("RN1360", "GW9"): ("GO9", "white", "off-white"),
}


def digits(value):
    return "".join(c for c in str(value) if c.isdigit())


def read_spec(path):
    """{(design, header, colour letter, length digit): barcode} from the spec.

    The spec writes its design codes inconsistently — RN1268, R12471, RK24539,
    RR1370 all appear — so only the digits are kept, which are unambiguous.
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.active
        spec, unknown, by_triple = {}, set(), {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not isinstance(row[2], (int, float)):
                continue
            colour = str(row[1]).strip()
            letter = COLOUR_LETTER.get(colour)
            if letter is None:
                unknown.add(colour)
                continue
            header = "G" if str(row[5]).strip().lower().startswith("grommet") else "R"
            length = "8" if int(row[2]) == 84 else "9"
            barcode = row[11]
            if barcode is None:
                continue
            spec[(digits(row[0]), header, letter, length)] = str(int(barcode))
            by_triple.setdefault((digits(row[0]), header, length), []).append(
                (colour, str(int(barcode))))
        # Where a design offers exactly ONE colourway for a given header and
        # length, the colour letter carries no information and the variant is
        # identified by the other three alone. RN1360's grommet panel is the
        # case that matters: the spec calls it Kirli Beyaz, the catalog and
        # the warehouse both call it white, so a letter-for-letter lookup
        # misses a variant that is not actually ambiguous.
        singles = {k: v[0] for k, v in by_triple.items() if len(v) == 1}
        return spec, unknown, singles
    finally:
        wb.close()


class Command(BaseCommand):
    help = "Align the ready-made curtain catalog with the Karven spec sheet."

    def add_arguments(self, parser):
        parser.add_argument("--spec", default=str(DEFAULT_SPEC),
                            help="Path to KarvenReadyMadeStock.xlsx")
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")

    def handle(self, *args, **options):
        spec_path = Path(options["spec"])
        if not spec_path.exists():
            raise CommandError(f"Spec sheet not found: {spec_path}")
        spec, unknown, singles = read_spec(spec_path)
        if unknown:
            self.stdout.write(self.style.WARNING(
                f"  spec colourways with no letter mapping: {sorted(unknown)}"))

        applied = options["apply"]
        try:
            with transaction.atomic():
                stats = self._run(spec, singles)
                if not applied:
                    raise _Rollback()
        except _Rollback:
            pass
        self._report(stats, applied)

    # ------------------------------------------------------------------
    def _run(self, spec, singles):
        stats = {"categorised": [], "renamed": [], "barcodes": [],
                 "created": [], "typo": None, "unparsed": [], "no_barcode": [],
                 "by_triple": [], "recoloured": [], "unfeatured": []}

        products = [p for p in Product.objects.filter(sku__istartswith="R")
                    if PARENT_RE.match(p.sku or "")]

        # 1. Butterfly, and anything else that lost its category.
        category = ProductCategory.objects.filter(name=CATEGORY).first()
        if category is None:
            raise CommandError(f"No {CATEGORY!r} product category")
        for p in products:
            if p.category_id != category.pk:
                stats["categorised"].append(f"{p.sku} {p.title}")
                p.category = category
                p.save(update_fields=["category"])

        # 2. The missing Dandelion variant, before the rename pass so it is
        #    normalised by the same code as everything else.
        parent = next((p for p in products if p.sku == NEW_VARIANT["parent"]), None)
        if parent is None:
            raise CommandError(f"No parent product {NEW_VARIANT['parent']}")
        wanted = f'{NEW_VARIANT["parent"]}.{NEW_VARIANT["suffix"]}'
        bare = wanted.replace(".", "")
        if not ProductVariant.objects.filter(
                variant_sku__in=(wanted, bare)).exists():
            sibling = parent.variants.first()
            variant = ProductVariant.objects.create(
                product=parent,
                variant_sku=wanted,
                variant_barcode=NEW_VARIANT["barcode"],
                variant_cost=NEW_VARIANT["cost"],
                # Priced off the sibling's own markup rather than a constant,
                # so the new panel sits on the same margin as the design's
                # other four instead of at a number picked here.
                variant_price=(
                    (NEW_VARIANT["cost"] * sibling.variant_price
                     / sibling.variant_cost).quantize(Decimal("0.01"))
                    if sibling and sibling.variant_cost else None),
            )
            for name, value in NEW_VARIANT["attributes"]:
                variant.product_variant_attribute_values.add(
                    self._attribute_value(name, value))
            stats["created"].append(f"{wanted}  {NEW_VARIANT['barcode']}")
            products = [p for p in Product.objects.filter(sku__istartswith="R")
                        if PARENT_RE.match(p.sku or "")]

        # 3 + 4. Normalise every SKU to PARENT.SUFFIX and fill in barcodes.
        for p in sorted(products, key=lambda x: x.sku):
            for v in p.variants.all():
                bare = v.variant_sku.replace(".", "")
                if not bare.upper().startswith(p.sku.upper()):
                    stats["unparsed"].append(v.variant_sku)
                    continue
                suffix = bare[len(p.sku):].upper()
                if len(suffix) != 3:
                    stats["unparsed"].append(v.variant_sku)
                    continue
                recolour = LETTER_FIX.get((p.sku, suffix))
                if recolour:
                    suffix, was, now = recolour
                    old = v.product_variant_attribute_values.filter(
                        product_variant_attribute__name="color",
                        product_variant_attribute_value=was).first()
                    if old:
                        v.product_variant_attribute_values.remove(old)
                        v.product_variant_attribute_values.add(
                            self._attribute_value("color", now))
                        stats["recoloured"].append(
                            f"{v.variant_sku:<14} color {was} -> {now}")
                wanted = f"{p.sku}.{suffix}"
                if v.variant_sku != wanted:
                    stats["renamed"].append(f"{v.variant_sku:<14} -> {wanted}")
                    v.variant_sku = wanted
                    v.save(update_fields=["variant_sku"])
                header, colour, length = suffix[0], suffix[1], suffix[2]
                barcode = spec.get((digits(p.sku), header, colour, length))
                if barcode is None:
                    single = singles.get((digits(p.sku), header, length))
                    if single:
                        barcode = single[1]
                        stats["by_triple"].append(
                            f"{wanted:<14} matched on header+length only "
                            f"(sole colourway: {single[0]})")
                if barcode is None:
                    stats["no_barcode"].append(wanted)
                elif (v.variant_barcode or "") != barcode:
                    stats["barcodes"].append(
                        f"{wanted:<14} {v.variant_barcode or '—':<14} -> {barcode}")
                    v.variant_barcode = barcode
                    v.save(update_fields=["variant_barcode"])

        # 5. Variants for combinations the spec does not manufacture. Wave is
        #    the only design with any: the catalog carries all eight
        #    header/colour/length permutations, Karven makes four. They have
        #    no barcode, no stock and nothing to scan, so they are taken off
        #    the storefront rather than deleted — an unfeature is reversible
        #    in the product editor, and a delete would be blocked anyway on
        #    any that ever reached an order line (OrderItem PROTECTs them).
        for sku in stats["no_barcode"]:
            v = ProductVariant.objects.filter(variant_sku=sku).first()
            if v and v.variant_featured:
                v.variant_featured = False
                v.save(update_fields=["variant_featured"])
                stats["unfeatured"].append(sku)

        # 6. Confetti's 132cm typo.
        psku, suffix, attr, wrong, right = TYPO_FIX
        v = ProductVariant.objects.filter(
            variant_sku__in=(f"{psku}.{suffix}", f"{psku}{suffix}")).first()
        if v:
            bad = v.product_variant_attribute_values.filter(
                product_variant_attribute__name=attr,
                product_variant_attribute_value=wrong).first()
            if bad:
                v.product_variant_attribute_values.remove(bad)
                v.product_variant_attribute_values.add(
                    self._attribute_value(attr, right))
                stats["typo"] = f"{v.variant_sku}  {wrong} -> {right}"
        return stats

    def _attribute_value(self, name, value):
        """An EXISTING attribute-value row, reused. Creating one would run it
        through save(), which underscores the spaces the stored rows contain
        and would fork "130 x 210 cm" into a second, unmatchable value.

        The one exception is a single-word value, which save() leaves alone —
        that is why the new variant's colour is "turquoise" and not a phrase.
        """
        existing = ProductVariantAttributeValue.objects.filter(
            product_variant_attribute__name=name,
            product_variant_attribute_value=value).first()
        if existing:
            return existing
        if " " in value:
            raise CommandError(
                f"Attribute value {name}={value!r} does not exist and cannot be "
                f"created safely — save() would store it as "
                f"{value.lower().replace(' ', '_')!r}.")
        from marketing.models import ProductVariantAttribute
        attribute = ProductVariantAttribute.objects.filter(name=name).first()
        if attribute is None:
            raise CommandError(f"No {name!r} product variant attribute")
        return ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attribute,
            product_variant_attribute_value=value)

    # ------------------------------------------------------------------
    def _report(self, s, applied):
        w = self.stdout.write
        w("")
        for title, rows in (("categorised", s["categorised"]),
                            ("created", s["created"]),
                            ("renamed", s["renamed"]),
                            ("barcodes set", s["barcodes"]),
                            ("recoloured", s["recoloured"]),
                            ("unfeatured (not in the spec)", s["unfeatured"])):
            w(f"  {title} ({len(rows)})")
            for row in rows:
                w(f"      {row}")
        if s["typo"]:
            w(f"  size typo fixed\n      {s['typo']}")
        if s["by_triple"]:
            w(f"  matched without the colour letter ({len(s['by_triple'])})")
            for row in s["by_triple"]:
                w(f"      {row}")
        if s["no_barcode"]:
            w(self.style.WARNING(
                f"  {len(s['no_barcode'])} variant(s) have no row in the spec "
                f"sheet, so no barcode:"))
            w("      " + ", ".join(s["no_barcode"]))
        if s["unparsed"]:
            w(self.style.ERROR(
                f"  {len(s['unparsed'])} variant SKU(s) do not read as "
                f"PARENT+3 and were left alone:"))
            w("      " + ", ".join(s["unparsed"]))
        w("")
        w(self.style.SUCCESS("Applied.") if applied else
          self.style.WARNING("Dry run — nothing written. Re-run with --apply."))


class _Rollback(Exception):
    """Unwinds the transaction at the end of a dry run."""
