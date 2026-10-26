"""What a stock item, or the part of one that ships, weighs.

Export papers need kilograms, and most stock items are never weighed: a
mill's label seldom prints them. So a weight comes from the best thing
known about the item:

1. its own weight, typed off its label at receipt, shared out by the
   quantity that ships — 30 m of a 50 m roll that weighed 45 kg is 27 kg;
2. for goods counted in meters, the product's GSM over the variant's
   width — 30 m of 320 gsm at 280 cm is 0.32 × 2.8 × 30 = 26.88 kg;
3. nothing. Never 0: a paper with a blank can be asked about, one that
   says 0 kg is just wrong.

The sack on the scale (Pack.gross_kg) is a different figure — packaging
included — and is never worked out, only typed.
"""
import re
from decimal import Decimal, InvalidOperation

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_KG = Decimal("0.01")


def width_cm(variant):
    """The variant's width in cm, read from its "width" value ("280"), or
    None when it has none or it isn't a number."""
    if variant is None:
        return None
    for v in variant.product_variant_attribute_values.all():
        if (v.product_variant_attribute.name or "").strip().lower() != "width":
            continue
        m = _NUMBER.search(v.product_variant_attribute_value or "")
        if m:
            try:
                return Decimal(m.group().replace(",", "."))
            except InvalidOperation:
                return None
    return None


def net_kg(quantity, stock_item=None, product=None, variant=None):
    """(kg, estimated) for `quantity` of a stock item; (None, False) when
    nothing says what it weighs. `estimated` is True for a weight worked
    out from GSM, False for one read off the item's label."""
    if quantity is None:
        return None, False
    quantity = Decimal(quantity)
    if stock_item is not None and stock_item.weight_kg and stock_item.quantity:
        share = stock_item.weight_kg * quantity / stock_item.quantity
        return share.quantize(_KG), False
    if product is not None and product.unit == "m" and product.gsm:
        width = width_cm(variant)
        if width:
            grams = product.gsm * width / 100 * quantity
            return (grams / 1000).quantize(_KG), True
    return None, False
