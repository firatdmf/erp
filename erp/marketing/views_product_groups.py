"""Product Group (ProductCategory) pages.

The product group is the DEFAULTS layer for its products: profit margin,
minimum order quantity, lead time, care instructions and the HS
(GTIP) code live here; every product in the group inherits them unless it
sets its own override (Product.effective_*). This replaces the old
hard-coded "suggested price" formula — pricing now flows from cost through
the group's margin, applied in bulk from the group page.
"""

from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _gettext
from django.views import View

from .attributes import normalize_attribute_name
from .models import (CategoryVariantAttribute, Product, ProductCategory,
                     ProductVariantAttribute, attach_live_costs,
                     with_product_live_quantity)


def _attribute_choices():
    """Every attribute name a group's preset can pick from."""
    return list(ProductVariantAttribute.objects.order_by("name").values_list("name", flat=True))


def _save_variant_attributes(group, request):
    """Replace the group's attribute preset with the posted list, in order.
    A name not in the catalog yet is added to it once, in the stored
    spelling (see marketing/attributes.py). Pages that don't send the
    list leave the preset alone."""
    if not request.POST.get("variant_attributes_sent"):
        return
    names = []
    for raw in request.POST.getlist("variant_attributes"):
        name = normalize_attribute_name(raw)
        if name and name not in names:
            names.append(name)
    with transaction.atomic():
        group.variant_attribute_presets.all().delete()
        for position, name in enumerate(names):
            attribute, _created = ProductVariantAttribute.objects.get_or_create(name=name)
            CategoryVariantAttribute.objects.create(
                category=group, attribute=attribute, position=position)


def _safe_decimal(value):
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _fill_group_settings(group, request):
    """Copy every group setting out of the request onto the (possibly unsaved)
    group — the create page and the settings page submit the same form.
    Returns what is wrong with them, or None.

    The price multiplier is required: every price in the group comes from
    it (marketing/pricing.py), and there is no default behind it."""
    from .pricing import parse_multiplier
    multiplier = (request.POST.get("price_multiplier") or "").strip()
    try:
        parse_multiplier(multiplier)
    except ValueError:
        return _gettext("Type what the cost is multiplied by, e.g. 4/3 or 3.")
    group.price_multiplier = multiplier
    group.description = (request.POST.get("description") or "").strip() or None
    group.is_active = request.POST.get("is_active") in ("1", "true", "on")
    group.minimum_order_quantity = _safe_decimal(request.POST.get("minimum_order_quantity"))
    lead = (request.POST.get("lead_time_days") or "").strip()
    group.lead_time_days = int(lead) if lead.isdigit() else None
    group.care_instructions = (request.POST.get("care_instructions") or "").strip() or None
    group.care_instructions_tr = (request.POST.get("care_instructions_tr") or "").strip() or None
    group.hs_code = (request.POST.get("hs_code") or "").strip()[:20] or None
    rule = request.POST.get("storefront_rule")
    if rule in dict(ProductCategory.STOREFRONT_RULES):
        group.storefront_rule = rule
    image_file = request.FILES.get("image")
    if image_file:
        group._image_file = image_file


@method_decorator(login_required, name="dispatch")
class ProductGroupList(View):
    """All product groups with live product counts; POST creates a new one."""

    def get(self, request):
        groups = (
            ProductCategory.objects
            .annotate(
                product_count=Count("product", distinct=True),
                featured_count=Count("product", filter=Q(product__featured=True), distinct=True),
            )
            .order_by("name")
        )
        ungrouped_count = Product.objects.filter(category__isnull=True).count()
        return render(request, "marketing/product_group_list.html", {
            "groups": groups,
            "ungrouped_count": ungrouped_count,
        })

    def post(self, request):
        # Kept for API-style use; the UI now goes through ProductGroupCreate,
        # which accepts the FULL settings form, not just a name.
        return ProductGroupCreate().post(request)


@method_decorator(login_required, name="dispatch")
class ProductGroupCreate(View):
    """Full-form group creation: the same settings cards as the group page
    (margin, min order, lead time, instructions, HS code, image, visibility)
    are all set in one go, so a group never starts as an empty shell."""

    def get(self, request):
        return render(request, "marketing/product_group_create.html", {
            "variant_attribute_names": _attribute_choices(),
        })

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        if not name:
            return JsonResponse({"success": False, "error": _gettext("The group name is required.")}, status=400)
        normalized = name.lower().strip().replace(" ", "_")
        existing = ProductCategory.objects.filter(name__iexact=normalized).first()
        if existing:
            return JsonResponse(
                {"success": False, "error": _gettext("A group with this name already exists."), "id": existing.pk},
                status=400,
            )
        group = ProductCategory(name=name)
        problem = _fill_group_settings(group, request)
        if problem:
            return JsonResponse({"success": False, "error": problem}, status=400)
        group.save()
        _save_variant_attributes(group, request)
        return JsonResponse({"success": True, "existed": False, "id": group.pk})


@method_decorator(login_required, name="dispatch")
class ProductGroupDetail(View):
    """One group's settings + its products. POST actions:
    save_settings / delete_group."""

    def get(self, request, pk):
        group = get_object_or_404(ProductCategory, pk=pk)
        products = (
            with_product_live_quantity(group.product_set.all())
            .select_related("primary_image")
            .prefetch_related("variants")
            .order_by("title")
        )
        # A variant's cost is read off its stock: all of them in one query.
        products = list(products)
        attach_live_costs(v for p in products for v in p.variants.all())
        rows = []
        total_stock = Decimal("0")
        costed = 0
        for p in products:
            variants = list(p.variants.all())
            v_count = len(variants)
            # Stock is the warehouse's answer, annotated in one query above.
            stock = p.live_quantity or Decimal("0")
            total_stock += stock
            # Costed on its variants: a product has no cost of its own.
            has_cost = any(v.live_cost for v in variants)
            if has_cost:
                costed += 1
            rows.append({
                "product": p,
                "variant_count": v_count,
                "stock": stock,
                "has_cost": has_cost,
                "multiplier_override": p.price_multiplier,
            })
        stats = {
            "product_count": len(rows),
            "variant_count": sum(r["variant_count"] for r in rows),
            "total_stock": total_stock,
            "costed_count": costed,
        }
        return render(request, "marketing/product_group_detail.html", {
            "group": group,
            "rows": rows,
            "stats": stats,
            "variant_attribute_names": _attribute_choices(),
        })

    def post(self, request, pk):
        group = get_object_or_404(ProductCategory, pk=pk)
        action = request.POST.get("action") or "save_settings"

        if action == "save_settings":
            return self._save_settings(request, group)
        if action == "delete_group":
            return self._delete_group(request, group)
        return JsonResponse({"success": False, "error": _gettext("Unknown action.")}, status=400)

    def _save_settings(self, request, group):
        name = (request.POST.get("name") or "").strip()
        if name:
            normalized = name.lower().strip().replace(" ", "_")
            clash = ProductCategory.objects.filter(name__iexact=normalized).exclude(pk=group.pk).first()
            if clash:
                return JsonResponse(
                    {"success": False, "error": _gettext("Another group with this name already exists.")},
                    status=400,
                )
            group.name = name

        problem = _fill_group_settings(group, request)
        if problem:
            return JsonResponse({"success": False, "error": problem}, status=400)
        group.save()
        _save_variant_attributes(group, request)
        return JsonResponse({"success": True, "name": group.name})

    def _delete_group(self, request, group):
        # Every product is in a group — its prices come from there — so a
        # group that still has products is not deleted out from under them.
        count = group.product_set.count()
        if count:
            return JsonResponse({"success": False, "error": _gettext(
                "Move this group's %(count)s products to another group first: "
                "every product needs a group.") % {"count": count}}, status=400)
        group.delete()
        return JsonResponse({"success": True, "orphaned_products": 0})
