"""Which variants the storefront shows, for a group that leaves it to a rule.

A product group either lets each variant's Featured tick be set by hand, or
follows the rule: a variant is shown while it has stock and a photo of its
own, and hidden otherwise; its product is shown while any of its variants
is. The storefront only ever reads the ticks, so the rule works by keeping
them right — here, whenever stock, a variant's photos, a product or its
group change (marketing/signals.py), and once an hour for whatever changed
behind those signals' backs (product_images.housekeep_now_and_then).
"""
from django.db.models import DecimalField, Exists, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

NO_STOCK = "no_stock"
NO_PHOTO = "no_photo"
BY_HAND = "by_hand"


def _with_stock_and_photo(variants):
    from operating.models import WarehouseProduct
    from .models import ProductFile

    stock = (WarehouseProduct.objects.filter(catalog_variant=OuterRef("pk"))
             .values("catalog_variant").annotate(total=Sum("quantity")).values("total"))
    photo = ProductFile.objects.filter(product_variant=OuterRef("pk"), file_type="image")
    return variants.annotate(
        stock_total=Coalesce(Subquery(stock), Value(0), output_field=DecimalField()),
        has_own_photo=Exists(photo))


def follows_rule(product):
    from .models import ProductCategory
    return bool(product.category_id) and \
        product.category.storefront_rule == ProductCategory.STOREFRONT_IN_STOCK_WITH_PHOTO


def hidden_reasons(product):
    """{variant pk: why the storefront hides it, or None when it shows it}."""
    variants = _with_stock_and_photo(product.variants.all())
    if not follows_rule(product):
        return {v.pk: None if v.variant_featured else BY_HAND for v in variants}
    return {v.pk: None if v.stock_total > 0 and v.has_own_photo
            else NO_STOCK if v.stock_total <= 0 else NO_PHOTO
            for v in variants}


def apply(product_ids=None):
    """Set the Featured ticks of every product in a rule-following group
    (only `product_ids`, when given) to what the rule says. Returns how many
    variants and products changed."""
    from .models import Product, ProductCategory, ProductVariant

    products = Product.objects.filter(
        category__storefront_rule=ProductCategory.STOREFRONT_IN_STOCK_WITH_PHOTO)
    if product_ids is not None:
        products = products.filter(pk__in=product_ids)
    shown_product = dict.fromkeys(products.values_list("pk", flat=True), False)
    if not shown_product:
        return 0, 0
    show, hide = [], []
    for pk, product_id, featured, stock, photo in _with_stock_and_photo(
            ProductVariant.objects.filter(product_id__in=shown_product)).values_list(
            "pk", "product_id", "variant_featured", "stock_total", "has_own_photo"):
        wanted = stock > 0 and photo
        shown_product[product_id] = shown_product[product_id] or wanted
        if wanted != featured:
            (show if wanted else hide).append(pk)
    # .update(), not save(): the ticks are the rule's output, and saving
    # would set off the very signals that called this.
    ProductVariant.objects.filter(pk__in=show).update(variant_featured=True)
    ProductVariant.objects.filter(pk__in=hide).update(variant_featured=False)
    flip_on = Product.objects.filter(
        pk__in=[pk for pk, shown in shown_product.items() if shown], featured=False)
    flip_off = Product.objects.filter(
        pk__in=[pk for pk, shown in shown_product.items() if not shown], featured=True)
    products_changed = flip_on.update(featured=True) + flip_off.update(featured=False)
    return len(show) + len(hide), products_changed


def apply_after_commit(product_ids):
    """apply() for these products once the change that called it is saved."""
    from django.db import transaction
    ids = [pk for pk in set(product_ids) if pk]
    if ids:
        transaction.on_commit(lambda: apply(ids))
