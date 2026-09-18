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
