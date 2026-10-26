"""Prices for the storefront, for signed-in trade customers only.

The site is trade-only, and what the house charges is for its customers,
not for whoever reads the page's data or the public product API. So
get_products and get_product send no price at all, and the storefront
asks here for the products it shows, with the customer's Bearer token
(authentication.client_tokens) — after the page has loaded, since the
pages themselves are cached for everybody alike.

The numbers are the same ones those endpoints used to send: worked out
from cost (marketing/pricing.py), a product's being its variants'
lowest, in USD and in each currency the site converts to.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from authentication.client_tokens import client_from
from erp.storefront import answers_in_storefront_language

from .models import ProductVariant

SKU_LIMIT = 200


@answers_in_storefront_language
@csrf_exempt
@require_http_methods(["POST"])
def prices(request):
    """POST {"product_skus": [...]} → {"products": {sku: {"price",
    "prices"}}, "variants": {variant sku: {"variant_price",
    "variant_prices"}}}. Unknown SKUs are left out."""
    from .pricing import live_prices
    from .utils.currency_service import convert_price, get_rates

    if client_from(request) is None:
        return JsonResponse({"error": "Sign in for pricing"}, status=401)
    try:
        skus = json.loads(request.body or "{}").get("product_skus") or []
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    skus = [str(sku).strip() for sku in skus if str(sku).strip()][:SKU_LIMIT]

    variants = list(ProductVariant.objects.filter(product__sku__in=skus)
                    .values_list("pk", "variant_sku", "product__sku"))
    variant_prices = live_prices([pk for pk, _sku, _product in variants])
    rates = get_rates()

    product_prices = {}
    out_variants = {}
    for pk, variant_sku, product_sku in variants:
        price = variant_prices.get(pk)
        out_variants[variant_sku] = {
            "variant_price": float(price) if price is not None else None,
            "variant_prices": convert_price(price, rates),
        }
        if price is not None and (product_prices.get(product_sku) is None
                                  or price < product_prices[product_sku]):
            product_prices[product_sku] = price
    out_products = {
        sku: {"price": float(price) if price is not None else None,
              "prices": convert_price(price, rates)}
        for sku in {product_sku for _pk, _sku, product_sku in variants}
        for price in [product_prices.get(sku)]
    }
    return JsonResponse({"products": out_products, "variants": out_variants})
