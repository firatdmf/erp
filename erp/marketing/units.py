"""What a product is counted in and how its stock is packed.

Both are facts about the main product: a white and a beige GREK are both
metres of cloth on rolls, in every warehouse that holds them. So they live
once, on marketing.Product, and every warehouse row and screen reads them
from there. They used to be stored per warehouse row as well, which let one
product's variants disagree with no way to tell which was right.
"""
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

# What a product is COUNTED IN. Codes and labels are English; Turkish belongs
# in the .po catalogue, not in the data.
UNIT_CHOICES = [
    ("mt", pgettext_lazy("unit", "Metre")),
    ("piece", pgettext_lazy("unit", "Piece")),
    ("pack", pgettext_lazy("unit", "Pack")),
    ("kg", pgettext_lazy("unit", "Kilogram")),
]
DEFAULT_UNIT = "mt"
UNIT_SHORT = {"mt": _("m"), "piece": _("pcs"),
              "pack": _("pack"), "kg": _("kg")}

# The storefront's older, coarser unit (Product.unit_of_measurement): it has
# no piece/pack distinction, so both are "units".
UNIT_TO_STOREFRONT = {"mt": "mt", "kg": "kg", "piece": "units", "pack": "units"}

# What the quantity COLUMN is headed. Metres of cloth are a length and kilos
# are a weight; a count of curtain sets is neither.
QUANTITY_LABEL = {"mt": _("Length"), "kg": _("Weight")}

# How a product's stock is PACKED — what one stock item physically is: a roll
# of cloth, a box of curtain sets, a bale of waste. Separate from the unit on
# purpose: metres can arrive on a bolt as easily as a roll, and pieces in a
# bag as easily as a box.
PACK_CHOICES = [
    ("roll", _("Roll")),
    ("box", _("Box")),
    ("bale", _("Bale")),
    ("bag", _("Bag")),
    ("bundle", _("Bundle")),
    ("pallet", _("Pallet")),
    # Not packed at all: pieces standing on a shelf. Still a pack TYPE,
    # because every product has to say how its stock is kept — this is
    # the answer "it isn't in anything".
    ("loose", _("Loose")),
]
DEFAULT_PACK = "roll"
# Packs that are not containers, so there is nothing to count: "22 pcs" is
# the whole of what there is to say, and "22 pcs · 1 box" would describe a
# box nobody can find. One stock entry of such a product is a batch — the
# pieces that arrived together at one cost.
UNCOUNTED_PACKS = frozenset({"loose"})
PACK_NOUN = {
    "roll": (_("roll"), _("rolls")),
    "box": (_("box"), _("boxes")),
    "bale": (_("bale"), _("bales")),
    "bag": (_("bag"), _("bags")),
    "bundle": (_("bundle"), _("bundles")),
    "pallet": (_("pallet"), _("pallets")),
    "loose": (_("batch"), _("batches")),
}
# Font Awesome class to match. A scroll for a roll of cloth, a carton for a
# box — the icon does as much of the telling as the word.
PACK_ICON = {"roll": "fa-scroll", "box": "fa-box", "bale": "fa-cubes-stacked",
             "bag": "fa-sack-xmark", "bundle": "fa-boxes-stacked",
             "pallet": "fa-pallet", "loose": "fa-layer-group"}

# The pack a unit starts on when nobody has said otherwise. A starting point,
# not a rule: the two can be set independently.
PACK_FOR_UNIT = {"mt": "roll", "kg": "bale", "piece": "box", "pack": "box"}


def unit_short(unit):
    """The unit as printed next to a number — "m", "pcs". A plain string, so
    it follows the request's language and drops straight into JSON."""
    return str(UNIT_SHORT.get(unit, unit or ""))


def pack_nouns(pack_type):
    """(singular, plural) for one stock item of this pack, as plain strings."""
    one, many = PACK_NOUN.get(pack_type, (_("item"), _("items")))
    return str(one), str(many)


def pack_noun(pack_type, count):
    """"roll" for one, "rolls" for any other count."""
    one, many = pack_nouns(pack_type)
    return one if count == 1 else many


# Units that count interchangeable things. A metre of cloth comes off one
# particular roll, which has a barcode of its own; a duvet set is one of
# many alike, and the barcode printed on it names the VARIANT — every set
# of it carries the same one. So such a product is sold by a quantity and
# its variant's barcode, never by picking out one labelled item.
COUNTED_UNITS = frozenset({"piece", "pack"})


def sold_by_count(unit):
    """Whether a product in this unit is sold as a count of alike pieces
    (see COUNTED_UNITS) rather than item by labelled item."""
    return unit in COUNTED_UNITS


def counts_packs(pack_type):
    """Whether a product packed this way has packs worth counting. False
    for loose stock — see UNCOUNTED_PACKS."""
    return pack_type not in UNCOUNTED_PACKS


def quantity_label(unit):
    return str(QUANTITY_LABEL.get(unit, _("Quantity")))
