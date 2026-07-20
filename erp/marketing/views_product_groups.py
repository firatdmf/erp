"""Product Group (ProductCategory) pages.

The product group is the DEFAULTS layer for its products: profit margin,
minimum order quantity, lead time, care instructions and the HS
(GTIP) code live here; every product in the group inherits them unless it
sets its own override (Product.effective_*). This replaces the old
hard-coded "suggested price" formula — pricing now flows from cost through
the group's margin, applied in bulk from the group page.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Product, ProductCategory, ProductVariant


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


def _apply_margin_price(cost, margin_pct):
    """price = cost x (1 + margin/100), rounded to 2 decimals."""
    return (cost * (Decimal("1") + margin_pct / Decimal("100"))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _fill_group_settings(group, request):
    """Copy every group setting out of the request onto the (possibly unsaved)
    group — the create page and the settings page submit the same form."""
    group.description = (request.POST.get("description") or "").strip() or None
    group.is_active = request.POST.get("is_active") in ("1", "true", "on")
    group.profit_margin = _safe_decimal(request.POST.get("profit_margin"))
    group.minimum_order_quantity = _safe_decimal(request.POST.get("minimum_order_quantity"))
    lead = (request.POST.get("lead_time_days") or "").strip()
    group.lead_time_days = int(lead) if lead.isdigit() else None
    group.care_instructions = (request.POST.get("care_instructions") or "").strip() or None
    group.care_instructions_tr = (request.POST.get("care_instructions_tr") or "").strip() or None
    group.hs_code = (request.POST.get("hs_code") or "").strip()[:20] or None
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
        return render(request, "marketing/product_group_create.html", {})

    def post(self, request):
        name = (request.POST.get("name") or "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "Grup adı gerekli."}, status=400)
        normalized = name.lower().strip().replace(" ", "_")
        existing = ProductCategory.objects.filter(name__iexact=normalized).first()
        if existing:
            return JsonResponse(
                {"success": False, "error": "Bu isimde bir grup zaten var.", "id": existing.pk},
                status=400,
            )
        group = ProductCategory(name=name)
        _fill_group_settings(group, request)
        group.save()
        return JsonResponse({"success": True, "existed": False, "id": group.pk})


@method_decorator(login_required, name="dispatch")
class ProductGroupDetail(View):
    """One group's settings + its products. POST actions:
    save_settings / apply_margin / delete_group."""

    def get(self, request, pk):
        group = get_object_or_404(ProductCategory, pk=pk)
        products = (
            group.product_set
            .select_related("primary_image")
            .prefetch_related("variants")
            .order_by("title")
        )
        rows = []
        total_stock = Decimal("0")
        costed = 0
        for p in products:
            variants = list(p.variants.all())
            v_count = len(variants)
            stock = p.quantity or Decimal("0")
            if variants:
                stock = sum((v.variant_quantity or Decimal("0")) for v in variants)
            total_stock += stock
            has_cost = bool(p.cost) or any(v.variant_cost for v in variants)
            if has_cost:
                costed += 1
            rows.append({
                "product": p,
                "variant_count": v_count,
                "stock": stock,
                "has_cost": has_cost,
                "margin_override": p.profit_margin,
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
        })

    def post(self, request, pk):
        group = get_object_or_404(ProductCategory, pk=pk)
        action = request.POST.get("action") or "save_settings"

        if action == "save_settings":
            return self._save_settings(request, group)
        if action == "apply_margin":
            return self._apply_margin(request, group)
        if action == "delete_group":
            return self._delete_group(request, group)
        return JsonResponse({"success": False, "error": "Bilinmeyen işlem."}, status=400)

    def _save_settings(self, request, group):
        name = (request.POST.get("name") or "").strip()
        if name:
            normalized = name.lower().strip().replace(" ", "_")
            clash = ProductCategory.objects.filter(name__iexact=normalized).exclude(pk=group.pk).first()
            if clash:
                return JsonResponse(
                    {"success": False, "error": "Bu isimde başka bir grup zaten var."},
                    status=400,
                )
            group.name = name

        _fill_group_settings(group, request)
        group.save()
        return JsonResponse({"success": True, "name": group.name})

    def _apply_margin(self, request, group):
        """Reprice the whole group from cost: price = cost x (1 + margin/100).
        A product's own profit_margin override wins over the group's. Rows
        without a cost are left untouched and reported back."""
        if group.profit_margin is None:
            return JsonResponse(
                {"success": False, "error": "Önce grubun kar oranını kaydedin."},
                status=400,
            )

        products = group.product_set.prefetch_related("variants")
        products_updated = 0
        variants_updated = 0
        skipped_no_cost = 0

        products_to_save = []
        variants_to_save = []
        for p in products:
            margin = p.profit_margin if p.profit_margin is not None else group.profit_margin
            touched = False
            if p.cost and p.cost > 0:
                p.price = _apply_margin_price(p.cost, margin)
                products_to_save.append(p)
                touched = True
            for v in p.variants.all():
                if v.variant_cost and v.variant_cost > 0:
                    v.variant_price = _apply_margin_price(v.variant_cost, margin)
                    variants_to_save.append(v)
                    touched = True
            if not touched:
                skipped_no_cost += 1

        if products_to_save:
            Product.objects.bulk_update(products_to_save, ["price"], batch_size=500)
            products_updated = len(products_to_save)
        if variants_to_save:
            ProductVariant.objects.bulk_update(variants_to_save, ["variant_price"], batch_size=500)
            variants_updated = len(variants_to_save)

        return JsonResponse({
            "success": True,
            "products_updated": products_updated,
            "variants_updated": variants_updated,
            "skipped_no_cost": skipped_no_cost,
        })

    def _delete_group(self, request, group):
        count = group.product_set.count()
        group.delete()   # Product.category is SET_NULL — products survive
        return JsonResponse({"success": True, "orphaned_products": count})
