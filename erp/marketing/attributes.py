"""How variant attribute names and values are spelled.

One rule for every writer — the product page, the goods-receipt form, roll
scanning and imports. Before this each wrote its own way, which is how the
catalog came to hold `color`, `Color` and `colır`, and "130 x 210cm" beside
"130 x 210 cm" (see ~/Backups/erp/catalog-cleanup-log.md, C1 and C2).

The storefront (demfirat) reads these as stored: it keys labels and filters
on the attribute NAME (`color`, `header`, anything containing `size`) and
parses sizes as "W x H cm" — so a size keeps its spaces, where every other
value is lower_case_with_underscores.
"""
import re

_SIZE_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?$", re.I)
_BARE_NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")


def normalize_attribute_name(name):
    """Lower case, single spaces: "Size  Per Panel" → "size per panel"."""
    return " ".join(str(name or "").lower().split())


def is_size_attribute(name):
    return "size" in normalize_attribute_name(name)


def normalize_attribute_value(attribute_name, value):
    """The stored spelling of one value of `attribute_name`.

    Sizes read "130 x 210 cm"; everything else "dark_cream". Colours use
    American spelling ("gray"), which is what the storefront's colour map
    and Muhammed both prefer.
    """
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if is_size_attribute(attribute_name):
        m = _SIZE_RE.match(text)
        if m:
            return f"{m.group(1)} x {m.group(2)} cm"
        return text.lower()
    text = text.lower().replace(" ", "_")
    if normalize_attribute_name(attribute_name) == "color":
        text = text.replace("grey", "gray")
    return text


def attribute_label(name):
    """How a stored attribute name is shown: "size per panel" → "Size per panel"."""
    name = normalize_attribute_name(name)
    return name[:1].upper() + name[1:]


def value_label(value):
    """How a stored value is shown: "dark_cream" → "Dark cream"."""
    text = str(value or "").replace("_", " ")
    return text[:1].upper() + text[1:]


def is_width_attribute(name):
    return normalize_attribute_name(name) == "width"


def display_value(attribute_name, value):
    """How one value of `attribute_name` reads on screen.

    The underscores are a storage habit, not something to read: a value
    is stored "cactus_green" and shown "Cactus green". A width is stored
    as the bare number the fabric is measured by ("250"), which in a
    column of variant values is a number with nothing to say what it
    measures — so it prints with its unit, "250 cm", the way a size
    already prints "160 x 200 cm". A width that was typed with a unit
    already ("150cm") is left as the person wrote it.
    """
    text = value_label(value)
    if is_width_attribute(attribute_name) and _BARE_NUMBER_RE.match(text):
        return f"{text} cm"
    return text
