"""What each supplier calls one of our variants — written by the purchase.

OUR SKU is the catalog variant's, and the warehouse row carries the same
one; a supplier's own code for the thing never goes in either. It goes
here, on the SupplierItem for (their account, our variant), captured when
somebody has their quotation or invoice in hand and is typing the purchase
anyway. From then on our SKU answers "what does each mill call this, and
what did they last charge", and their SKU finds our variant.
"""
from decimal import Decimal

from django.utils.translation import gettext as _

from .models import SKU_MAX_LENGTH, SupplierItem


class SupplierSkuTaken(Exception):
    """This supplier already uses the code for another of our variants."""

    def __init__(self, supplier_sku, item):
        self.item = item
        super().__init__(
            _("%(account)s already uses supplier SKU '%(sku)s' for %(variant)s.")
            % {"account": item.current_account.name, "sku": supplier_sku,
               "variant": item.variant.variant_sku})


def record_purchase(account, variant, *, supplier_sku=None, unit_price=None,
                    currency="", on_date=None):
    """Note that `account` sold us `variant`: their code for it, when one was
    typed, and what they charged.

    `supplier_sku` None leaves their code as it stands — a caller that has no
    field for it must not wipe one. An empty string clears it. The price only
    moves forward: a purchase dated before the one already on the row (an old
    one being corrected) doesn't become "the last price".

    Raises SupplierSkuTaken, having written nothing, when they already use
    the code for a different variant: one of their codes means one of our
    variants, or their invoice line can't be matched to anything. Returns
    the SupplierItem.
    """
    if account is None or variant is None:
        return None
    item = SupplierItem.objects.filter(current_account=account, variant=variant).first()
    if item is None:
        item = SupplierItem(current_account=account, variant=variant)

    if supplier_sku is not None:
        supplier_sku = str(supplier_sku).strip()[:SKU_MAX_LENGTH]
        if supplier_sku and supplier_sku != item.supplier_sku:
            clash = (SupplierItem.objects
                     .filter(current_account=account, supplier_sku__iexact=supplier_sku)
                     .exclude(pk=item.pk).select_related("current_account", "variant").first())
            if clash is not None:
                raise SupplierSkuTaken(supplier_sku, clash)
        item.supplier_sku = supplier_sku

    price = Decimal(str(unit_price)) if unit_price not in (None, "") else None
    if price is not None and price > 0 and (
            item.last_purchased_at is None or on_date is None
            or on_date >= item.last_purchased_at):
        item.last_unit_price = price
        item.last_price_currency = (currency or "")[:4]
        if on_date is not None:
            item.last_purchased_at = on_date
    item.save()
    return item


def set_code(item, supplier_sku):
    """Correct what `item`'s supplier calls its variant — from the product
    page, where a code attached to the wrong variant is put right. Blank
    clears it. Raises SupplierSkuTaken if they use it for another variant."""
    supplier_sku = str(supplier_sku or "").strip()[:SKU_MAX_LENGTH]
    if supplier_sku:
        clash = holder_of(item.current_account, supplier_sku)
        if clash is not None and clash.pk != item.pk:
            raise SupplierSkuTaken(supplier_sku, clash)
    item.supplier_sku = supplier_sku
    item.save(update_fields=["supplier_sku", "updated_at"])
    return item


def holder_of(account, supplier_sku):
    """The SupplierItem that has `account`'s code, or None."""
    supplier_sku = (supplier_sku or "").strip()
    if account is None or not supplier_sku:
        return None
    return (SupplierItem.objects
            .filter(current_account=account, supplier_sku__iexact=supplier_sku)
            .select_related("current_account", "variant__product").first())


def codes_of(account):
    """Every code we know `account` by, with the variant of ours each one
    means — what the purchase page suggests from and checks a typed code
    against. Another supplier's codes are never in it."""
    if account is None:
        return []
    items = (SupplierItem.objects.filter(current_account=account).exclude(supplier_sku="")
             .select_related("variant__product").order_by("supplier_sku"))
    return [{"supplier_sku": i.supplier_sku, "variant_sku": i.variant.variant_sku,
             "product_id": i.variant.product_id,
             "product": i.variant.product.title or "",
             "product_sku": i.variant.product.sku or ""}
            for i in items]


def find_variant(account, supplier_sku):
    """Our variant for one of `account`'s codes, or None."""
    supplier_sku = (supplier_sku or "").strip()
    if account is None or not supplier_sku:
        return None
    item = (SupplierItem.objects
            .filter(current_account=account, supplier_sku__iexact=supplier_sku)
            .select_related("variant__product").first())
    return item.variant if item is not None else None


def suppliers_of(variant_ids):
    """{variant_id: [who sells it, as the purchase page lists them]} —
    preferred first, then the most recently bought from."""
    out = {}
    items = (SupplierItem.objects.filter(variant_id__in=list(variant_ids))
             .select_related("current_account")
             .order_by("-is_preferred", "-last_purchased_at", "current_account__name"))
    for item in items:
        out.setdefault(item.variant_id, []).append({
            "account_id": item.current_account_id,
            "account": item.current_account.name,
            "supplier_sku": item.supplier_sku,
            "last_price": (float(item.last_unit_price)
                           if item.last_unit_price is not None else None),
            "currency": item.last_price_currency,
            "last_purchased_at": (item.last_purchased_at.isoformat()
                                  if item.last_purchased_at else ""),
            "preferred": item.is_preferred,
        })
    return out
