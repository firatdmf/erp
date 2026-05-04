"""
Public storefront API. Belino Next.js bu endpoint'leri çağırıp
header navı ve anasayfa bölümlerini render eder.

Hızlı/cache'lenebilir olması için DRF değil sade JsonResponse + nested
dict serialization kullanıyoruz. ISR ile Next.js zaten cache'liyor.
"""
import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import (
    Storefront, NavMenu, HomeSection, HomeSectionCard,
    HomeSectionProduct, TrustBadge,
)


def _resolve_category_id(item: NavMenu) -> int | None:
    """Find the ProductCategory id behind a nav item.

    Tries the explicit FK first, then falls back to parsing the slug out
    of `?cat=<slug>` in the href so editor-created nav items that the
    operator never bothered to link still get a real product count.
    """
    if item.category_id:
        return item.category_id
    href = item.href or ""
    if "cat=" in href:
        try:
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(href).query)
            slug = (qs.get("cat") or [""])[0].strip().lower()
            if slug:
                from marketing.models import ProductCategory
                cat = ProductCategory.objects.filter(name=slug).first()
                if cat:
                    return cat.id
        except Exception:
            pass
    return None


def _serialize_nav_item(item: NavMenu) -> dict:
    children = [_serialize_nav_item(c) for c in item.children.filter(is_active=True).order_by("order", "id")]
    # Product count for the nav item's resolved category (drives the
    # "X ürün" badge in the front-end mega menu).
    count = 0
    cat_id = _resolve_category_id(item)
    if cat_id:
        from marketing.models import Product
        count = Product.objects.filter(category_id=cat_id).count()
    return {
        "id": item.id,
        "key": f"nav-{item.id}",
        "label": {"tr": item.label_tr, "en": item.label_en},
        "href": item.href or "",
        "swatch": item.swatch or "",
        "count": count,
        "feature": (
            {
                "title": item.feature_title,
                "meta": item.feature_meta,
                "image": item.feature_image_url,
            }
            if (item.feature_title or item.feature_image_url)
            else None
        ),
        "children": children,
    }


@require_GET
def api_nav(request, key: str):
    """Header navigasyonu — top-level + children ağacı."""
    storefront = get_object_or_404(Storefront, key=key, is_active=True)
    items = (
        NavMenu.objects
        .filter(storefront=storefront, parent__isnull=True, is_active=True)
        .order_by("order", "id")
        .prefetch_related("children")
    )
    data = {
        "storefront": {"key": storefront.key, "name": storefront.name},
        "items": [_serialize_nav_item(it) for it in items],
    }
    resp = JsonResponse(data)
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Cache-Control"] = "public, max-age=60"
    return resp


def _serialize_section(section: HomeSection) -> dict:
    base = {
        "id": section.id,
        "kind": section.kind,
        "eyebrow": {"tr": section.eyebrow_tr, "en": section.eyebrow_en},
        "title": {"tr": section.title_tr, "en": section.title_en},
        "body": {"tr": section.body_tr, "en": section.body_en},
        "image": section.image_url,
        "cta": (
            {
                "label": {"tr": section.cta_label_tr, "en": section.cta_label_en},
                "href": section.cta_href,
            }
            if section.cta_label_tr or section.cta_label_en
            else None
        ),
    }

    if section.kind == HomeSection.KIND_SEASONS:
        base["cards"] = [
            {
                "id": c.id,  # HomeSectionCard.pk → reorder API'a gönderilir
                "key": c.key,
                "label": {"tr": c.label_tr, "en": c.label_en},
                "eyebrow": {"tr": c.eyebrow_tr, "en": c.eyebrow_en},
                "image": c.image_url,
                "href": c.href,
                "count": c.item_count,
            }
            for c in section.cards.all().order_by("order", "id")
        ]
    elif section.kind == HomeSection.KIND_FEATURED:
        base["products"] = [
            {
                "id": p.id,  # HomeSectionProduct.pk → reorder API'a gönderilir
                "product_id": p.product_id,
                "sku": p.product.sku,
            }
            for p in section.featured_products.select_related("product").order_by("order", "id")
        ]
    elif section.kind == HomeSection.KIND_TRUST:
        base["badges"] = [
            {
                "id": b.id,
                "icon": b.icon_key,
                "title": {"tr": b.title_tr, "en": b.title_en},
                "sub": {"tr": b.sub_tr, "en": b.sub_en},
            }
            for b in section.badges.all().order_by("order", "id")
        ]
    return base


@require_GET
def api_home(request, key: str):
    """Anasayfa bölümleri — sırasıyla."""
    storefront = get_object_or_404(Storefront, key=key, is_active=True)
    sections = (
        HomeSection.objects
        .filter(storefront=storefront, is_active=True)
        .order_by("order", "id")
        .prefetch_related("cards", "featured_products", "featured_products__product", "badges")
    )
    data = {
        "storefront": {"key": storefront.key, "name": storefront.name},
        "sections": [_serialize_section(s) for s in sections],
    }
    resp = JsonResponse(data)
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Cache-Control"] = "public, max-age=60"
    return resp


# --------------------------------------------------------------------------
# Reorder (drag-drop) — admin only. Body: {"items": [{"id": 1, "order": 0}, ...]}
# --------------------------------------------------------------------------
REORDER_MODELS = {
    "navmenu": NavMenu,
    "homesection": HomeSection,
    "homesectioncard": HomeSectionCard,
    "homesectionproduct": HomeSectionProduct,
    "trustbadge": TrustBadge,
}


@login_required
@require_POST
def api_reorder(request, model: str):
    Model = REORDER_MODELS.get(model)
    if Model is None:
        return HttpResponseBadRequest("unknown model")
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("invalid json")
    items = payload.get("items") or []
    if not isinstance(items, list):
        return HttpResponseBadRequest("items must be a list")

    # Bulk-update: tek query'de yapmak için id->order map
    order_by_id = {}
    for it in items:
        try:
            order_by_id[int(it["id"])] = int(it["order"])
        except (KeyError, TypeError, ValueError):
            continue
    if not order_by_id:
        return JsonResponse({"updated": 0})

    objs = list(Model.objects.filter(id__in=order_by_id.keys()))
    for obj in objs:
        obj.order = order_by_id[obj.id]
    Model.objects.bulk_update(objs, ["order"])
    return JsonResponse({"updated": len(objs)})


@login_required
@require_POST
def api_toggle_active(request, model: str, pk: int):
    """Pill'e tıkla → aktif/pasif. Tek field flip + JSON döner."""
    Model = REORDER_MODELS.get(model)
    if Model is None or not hasattr(Model, "is_active"):
        return HttpResponseBadRequest("unsupported")
    obj = get_object_or_404(Model, pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return JsonResponse({"id": obj.id, "is_active": obj.is_active})


# Inline text editing — `?edit=1` Belino sayfasında metne tıklayınca
# burası çağrılır. Allowlist sınırlı; rasgele field güncellenemiyor.
TEXT_EDIT_FIELDS = {
    "homesection": {
        "eyebrow_tr", "eyebrow_en", "title_tr", "title_en",
        "body_tr", "body_en", "cta_label_tr", "cta_label_en", "cta_href",
        "image_url",
    },
    "homesectioncard": {
        "label_tr", "label_en", "eyebrow_tr", "eyebrow_en",
        "image_url", "href",
    },
    "trustbadge": {"title_tr", "title_en", "sub_tr", "sub_en"},
    "navmenu": {
        "label_tr", "label_en", "feature_title", "feature_meta",
        "feature_image_url", "href",
    },
}


@login_required
@require_POST
def api_save_text(request, model: str, pk: int):
    """Inline text edit: body `{field, value}`."""
    Model = REORDER_MODELS.get(model)
    allowed = TEXT_EDIT_FIELDS.get(model, set())
    if Model is None or not allowed:
        return HttpResponseBadRequest("unsupported model")
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("invalid json")
    field = payload.get("field", "")
    value = payload.get("value", "")
    if field not in allowed:
        return HttpResponseBadRequest(f"field '{field}' not editable")
    obj = get_object_or_404(Model, pk=pk)
    setattr(obj, field, value)
    obj.save(update_fields=[field])
    return JsonResponse({"ok": True, "id": obj.id, "field": field, "value": value})


@csrf_exempt  # cross-origin from Belino iframe; login_required is the gate
@login_required
@require_POST
def api_save_image(request, model: str, pk: int):
    """Inline image change: multipart `field=<name>&file=<image>`."""
    Model = REORDER_MODELS.get(model)
    allowed = TEXT_EDIT_FIELDS.get(model, set())
    if Model is None or not allowed:
        return HttpResponseBadRequest("unsupported model")
    field = request.POST.get("field", "")
    if field not in allowed:
        return HttpResponseBadRequest(f"field '{field}' not editable")
    upload = request.FILES.get("file")
    if not upload:
        return HttpResponseBadRequest("no file")
    try:
        from marketing.utils.bunny_storage import upload_to_bunny
    except Exception:
        return JsonResponse({"ok": False, "error": "bunny unavailable"}, status=500)
    safe_name = upload.name.replace(" ", "_")
    path = f"media/storefront/inline/{model}-{pk}-{field}-{safe_name}"
    try:
        url = upload_to_bunny(upload, path)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    obj = get_object_or_404(Model, pk=pk)
    setattr(obj, field, url)
    obj.save(update_fields=[field])
    return JsonResponse({"ok": True, "id": obj.id, "field": field, "url": url})
