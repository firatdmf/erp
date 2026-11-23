"""What a stock item, or the part of one that ships, weighs.

Export papers need kilograms, and most stock items are never weighed: a
mill's label seldom prints them. So a weight comes from the best thing
known about the item:

1. its own weight, typed off its label at receipt, shared out by the
   quantity that ships — 30 m of a 50 m roll that weighed 45 kg is 27 kg;
2. what the same variant's weighed items say: the median of their kilos
   per unit — 30 m where its weighed rolls run 0.166 kg/m is 4.98 kg.
   Taken before a typed GSM: it is this very cloth, measured, where a
   product's GSM covers every variant, a pleated one and a plain alike;
3. for goods counted in meters, the product's GSM over the variant's
   width — 30 m of 320 gsm at 280 cm is 0.32 × 2.8 × 30 = 26.88 kg;
4. nothing. Never 0: a paper with a blank can be asked about, one that
   says 0 kg is just wrong.

The sack on the scale (Pack.gross_kg) is a different figure — packaging
included — and is never worked out, only typed.
"""
import re
from decimal import Decimal, InvalidOperation

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_KG = Decimal("0.01")
_UNSET = object()


def _median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _weighed_items(**filters):
    """(variant id, kg, quantity) of every stock item ever weighed —
    used up ones too: a roll weighed at receipt says what the cloth
    weighs whether or not any of it is left."""
    from operating.models import WarehouseProductItem
    return (WarehouseProductItem.objects
            .filter(weight_kg__gt=0, quantity__gt=0, **filters)
            .values_list("product__catalog_variant_id", "weight_kg", "quantity"))


def measured_kg_per_unit(variant):
    """The median kilos per unit (meter, piece…) of the variant's weighed
    stock items, or None when none was weighed. Kept on the variant, so
    a page asking for many lines of it asks the database once."""
    if variant is None or variant.pk is None:
        return None
    cached = getattr(variant, "_measured_kg_per_unit", _UNSET)
    if cached is _UNSET:
        cached = _median([kg / qty for _, kg, qty in
                          _weighed_items(product__catalog_variant=variant)])
        variant._measured_kg_per_unit = cached
    return cached


def measured_gsm(product):
    """(gsm, items) the product's weighed rolls work out to — each roll's
    kilos over its length times its variant's width, the median of them —
    or (None, 0). Only goods counted in meters, only variants with a
    width; shown beside a GSM nobody typed, never stored."""
    if product is None or product.pk is None or product.unit != "m":
        return None, 0
    widths = {}
    for variant in product.variants.prefetch_related(
            "product_variant_attribute_values__product_variant_attribute"):
        width = width_cm(variant)
        if width:
            widths[variant.pk] = width
    if not widths:
        return None, 0
    per_roll = [kg * 1000 / (qty * widths[vid] / 100)
                for vid, kg, qty in _weighed_items(product__catalog_variant_id__in=widths)]
    gsm = _median(per_roll)
    return (gsm.quantize(Decimal("1")) if gsm is not None else None), len(per_roll)


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
    out from the variant's other weighed items or from GSM, False for one
    read off the item's label."""
    if quantity is None:
        return None, False
    quantity = Decimal(quantity)
    if stock_item is not None and stock_item.weight_kg and stock_item.quantity:
        share = stock_item.weight_kg * quantity / stock_item.quantity
        return share.quantize(_KG), False
    per_unit = measured_kg_per_unit(variant)
    if per_unit is not None:
        return (per_unit * quantity).quantize(_KG), True
    if product is not None and product.unit == "m" and product.gsm:
        width = width_cm(variant)
        if width:
            grams = product.gsm * width / 100 * quantity
            return (grams / 1000).quantize(_KG), True
    return None, False
