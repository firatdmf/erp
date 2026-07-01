"""Perakende (retail / quick POS) order flow.

Pick products from warehouse stock + set unit prices → a PENDING retail order.
Later (even from a phone) scan the physical tops (rolls) to fulfil it: each scan
defaults to the roll's remaining metres and is editable DOWN for a partial cut
(the roll keeps the remainder — it is not fully consumed). On completion the
scanned metres are stocked out from their rolls.

Retail orders are Order rows with order_type='retail'; the scanned tops live in
RetailScan until completion. The catalog-deduct signal is exempted for retail
(see signals.py) because stock-out here is warehouse-scan driven.
"""
import json
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from .models import (
    Order, OrderItem, RetailScan, Warehouse, WarehouseProduct,
    WarehouseProductRoll, StockMovement,
)

_FOLD = str.maketrans({
    "İ": "I", "I": "I", "ı": "I", "Ş": "S", "ş": "S", "Ğ": "G", "ğ": "G",
    "Ü": "U", "ü": "U", "Ö": "O", "ö": "O", "Ç": "C", "ç": "C",
})


def _skukey(s):
    """Punctuation-insensitive, Turkish-folded SKU key for matching."""
    return re.sub(r"[^A-Z0-9]", "", ("" if s is None else str(s).strip().upper().translate(_FOLD)))


def _auth(request):
    return bool(getattr(request.user, "is_authenticated", False))


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _roll_remaining(roll):
    rem = roll.meters_remaining if roll.meters_remaining is not None else (roll.meters or Decimal("0"))
    return rem or Decimal("0")


def retail_new(request):
    """Page: create a Perakende order — pick warehouse products + set prices."""
    if not _auth(request):
        return redirect("authentication:signin")
    warehouses = list(Warehouse.objects.order_by("name").values("id", "name"))
    return render(request, "operating/retail_new.html", {"warehouses": warehouses})


def retail_scan_page(request, order_pk):
    """Page: scan the physical tops for a Perakende order and complete it."""
    if not _auth(request):
        return redirect("authentication:signin")
    order = get_object_or_404(Order, pk=order_pk, order_type="retail")
    return render(request, "operating/retail_scan.html", {"order": order})


def retail_product_list(request):
    """In-stock warehouse products across ALL warehouses — the retail picker
    source. Optional ?q= filters by name/sku, ?warehouse= scopes to one."""
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    q = (request.GET.get("q") or "").strip()
    wh = (request.GET.get("warehouse") or "").strip()
    qs = (WarehouseProduct.objects.filter(quantity__gt=0)
          .exclude(sku__isnull=True).exclude(sku="")
          .select_related("warehouse", "catalog_variant"))
    if wh.isdigit():
        qs = qs.filter(warehouse_id=int(wh))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    qs = qs.order_by("warehouse__name", "name")[:800]
    out = []
    for p in qs:
        cv = p.catalog_variant
        price = getattr(cv, "variant_price", None) if cv is not None else None
        out.append({
            "id": p.id, "name": p.name, "sku": p.sku,
            "warehouse": p.warehouse.name if p.warehouse_id else "",
            "warehouse_id": p.warehouse_id,
            "quantity": float(p.quantity or 0),
            "price": float(price) if price else None,
        })
    return JsonResponse({"success": True, "products": out})


def retail_order_create(request):
    """POST: create a PENDING retail order from selected warehouse products +
    unit prices. Body JSON: {items:[{warehouse_product_id, price}], notes?}."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    try:
        data = json.loads((request.body or b"").decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Geçersiz veri."}, status=400)
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return JsonResponse({"success": False, "error": "En az bir ürün seçin."}, status=400)
    notes = (data.get("notes") or "").strip() or None

    order = None
    try:
        with transaction.atomic():
            order = Order.objects.create(order_type="retail", status="pending", notes=notes)
            created = 0
            seen = set()
            for it in items:
                wpid = it.get("warehouse_product_id")
                if wpid in seen:
                    continue
                wp = (WarehouseProduct.objects
                      .filter(pk=wpid)
                      .select_related("catalog_variant__product").first())
                if wp is None:
                    continue
                seen.add(wpid)
                price = _dec(it.get("price")) or Decimal("0")
                cv = wp.catalog_variant
                OrderItem.objects.create(
                    order=order,
                    product=cv.product if (cv and cv.product_id) else None,
                    product_variant=cv if cv else None,
                    warehouse_product=wp,
                    price=price, quantity=Decimal("0"),
                    description=wp.name,
                )
                created += 1
            if not created:
                raise ValueError("no valid items")
    except ValueError:
        return JsonResponse({"success": False, "error": "Geçerli ürün bulunamadı."}, status=400)

    return JsonResponse({"success": True, "order_id": order.pk})


def _order_scan_state(order):
    """Serialize an order's selected lines + their scanned tops (for the scan UI)."""
    lines = []
    for oi in order.items.select_related("warehouse_product").all().order_by("id"):
        scans = [{
            "id": s.id, "barcode": (s.roll.barcode if s.roll_id else "") or "",
            "meters": float(s.meters or 0),
            "roll_remaining": float(_roll_remaining(s.roll)) if s.roll_id else 0,
        } for s in oi.retail_scans.filter(applied=False).select_related("roll").order_by("id")]
        lines.append({
            "order_item_id": oi.id,
            "name": (oi.warehouse_product.name if oi.warehouse_product_id else (oi.description or "")),
            "sku": (oi.warehouse_product.sku if oi.warehouse_product_id else ""),
            "price": float(oi.price or 0),
            "quantity": float(oi.quantity or 0),
            "scans": scans,
        })
    return lines


def retail_order_scans(request, order_pk):
    """GET: current lines + scans for an order (to resume scanning later)."""
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    order = get_object_or_404(Order, pk=order_pk, order_type="retail")
    return JsonResponse({"success": True, "order_id": order.pk, "status": order.status,
                         "lines": _order_scan_state(order)})


def retail_scan_add(request, order_pk):
    """POST {barcode}: match a scanned top to a selected line and add it. Default
    metres = the roll's remaining; editable later. Warns if the top's product
    isn't one of the selected products, or the top is already added/empty."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    order = get_object_or_404(Order, pk=order_pk, order_type="retail")
    if order.status == "completed":
        return JsonResponse({"success": False, "error": "Sipariş zaten tamamlandı."}, status=400)

    code = (request.POST.get("barcode") or "").strip()
    if not code and request.body and "application/json" in (request.content_type or ""):
        try:
            code = (json.loads(request.body.decode("utf-8") or "{}").get("barcode") or "").strip()
        except (ValueError, UnicodeDecodeError):
            code = ""
    if not code:
        return JsonResponse({"success": False, "error": "Barkod yok."}, status=400)

    roll = (WarehouseProductRoll.objects.filter(barcode__iexact=code)
            .select_related("product", "product__warehouse").first())
    if roll is None:
        return JsonResponse({"success": False, "error": f"'{code}' barkodlu top bulunamadı."})
    wp = roll.product
    if RetailScan.objects.filter(order=order, roll=roll, applied=False).exists():
        return JsonResponse({"success": False, "error": "Bu top zaten eklendi."})

    key = _skukey(wp.sku) if wp else ""
    match = None
    for oi in order.items.select_related("warehouse_product").all():
        wsku = oi.warehouse_product.sku if oi.warehouse_product_id else None
        if wsku and _skukey(wsku) == key and key:
            match = oi
            break
    if match is None:
        pname = wp.name if wp else code
        return JsonResponse({"success": False,
                             "error": f"'{pname}' bu siparişte seçili değil — eklenemez."})

    remaining = _roll_remaining(roll)
    if remaining <= 0:
        return JsonResponse({"success": False, "error": "Bu top tükenmiş (0 m)."})

    with transaction.atomic():
        scan = RetailScan.objects.create(
            order=order, order_item=match, roll=roll, warehouse_product=wp, meters=remaining)
        match.quantity = (match.quantity or Decimal("0")) + remaining
        match.save(update_fields=["quantity", "updated_at"])

    return JsonResponse({
        "success": True,
        "scan": {
            "id": scan.id, "barcode": roll.barcode or "", "meters": float(remaining),
            "roll_remaining": float(remaining), "order_item_id": match.id,
            "product_name": wp.name if wp else "", "price": float(match.price or 0),
            "warehouse": (wp.warehouse.name if (wp and wp.warehouse_id) else ""),
            "line_quantity": float(match.quantity or 0),
        },
        "message": f"Bu kupondan {remaining:g} metre düşülecektir.",
    })


def retail_scan_update(request, scan_pk):
    """POST {meters}: change how much to cut from a scanned top (partial cut).
    Clamped to (0, roll remaining]."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    scan = get_object_or_404(RetailScan, pk=scan_pk, applied=False)
    m = _dec(request.POST.get("meters"))
    if m is None or m <= 0:
        return JsonResponse({"success": False, "error": "Geçerli metre girin."}, status=400)
    cap = _roll_remaining(scan.roll) if scan.roll_id else m
    if m > cap:
        return JsonResponse({"success": False, "error": f"Bu topta en fazla {cap:g} m var."})
    with transaction.atomic():
        oi = scan.order_item
        if oi is not None:
            oi.quantity = max(Decimal("0"), (oi.quantity or Decimal("0")) - (scan.meters or Decimal("0")) + m)
            oi.save(update_fields=["quantity", "updated_at"])
        scan.meters = m
        scan.save(update_fields=["meters"])
    return JsonResponse({"success": True, "meters": float(m),
                         "line_quantity": float(oi.quantity or 0) if oi else 0,
                         "message": f"Bu kupondan {m:g} metre düşülecektir."})


def retail_scan_remove(request, scan_pk):
    """POST: remove a scanned top from the order (before completion)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    scan = get_object_or_404(RetailScan, pk=scan_pk, applied=False)
    line_qty = 0
    with transaction.atomic():
        oi = scan.order_item
        if oi is not None:
            oi.quantity = max(Decimal("0"), (oi.quantity or Decimal("0")) - (scan.meters or Decimal("0")))
            oi.save(update_fields=["quantity", "updated_at"])
            line_qty = float(oi.quantity or 0)
        scan.delete()
    return JsonResponse({"success": True, "line_quantity": line_qty})


def retail_complete(request, order_pk):
    """POST: finalize the order — stock out each scanned top's metres from its
    roll (partial-safe), log StockMovement(out), mark the order completed."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    if not _auth(request):
        return JsonResponse({"success": False, "error": "auth"}, status=403)
    order = get_object_or_404(Order, pk=order_pk, order_type="retail")
    if order.status == "completed":
        return JsonResponse({"success": False, "error": "Sipariş zaten tamamlandı."}, status=400)
    scans = list(RetailScan.objects.filter(order=order, applied=False)
                 .select_related("roll", "roll__product"))
    if not scans:
        return JsonResponse({"success": False, "error": "Önce en az bir top okutun."}, status=400)

    from django.db.models import Sum, F
    from django.db.models.functions import Coalesce
    user = request.user if _auth(request) else None
    touched = set()
    with transaction.atomic():
        for scan in scans:
            roll = scan.roll
            if roll is None:
                scan.applied = True
                scan.save(update_fields=["applied"])
                continue
            avail = _roll_remaining(roll)
            take = min(scan.meters or Decimal("0"), avail)
            roll.meters_remaining = avail - take
            if roll.meters_remaining <= 0:
                roll.status = "consumed"
            elif roll.meters_remaining < (roll.meters or Decimal("0")):
                roll.status = "partial"
            roll.save(update_fields=["meters_remaining", "status"])
            if roll.product_id:
                touched.add(roll.product_id)
                StockMovement.objects.create(
                    product_id=roll.product_id, roll=roll, movement_type="out",
                    quantity=take, reason=f"Perakende sipariş #{order.pk}",
                    reference=f"retail#{order.pk}", created_by=user,
                )
            scan.applied = True
            scan.save(update_fields=["applied"])
        # Recompute each touched product's denormalized quantity from ALL its
        # rolls (avoids stale per-roll product instances double-writing).
        for wpid in touched:
            agg = (WarehouseProductRoll.objects.filter(product_id=wpid)
                   .aggregate(s=Sum(Coalesce(F("meters_remaining"), F("meters")))))
            WarehouseProduct.objects.filter(pk=wpid).update(quantity=agg["s"] or Decimal("0"))
        order.status = "completed"
        # Retail is exempt from the catalog-deduct signal, so setting a
        # customer-facing 'delivered' status is safe (no double stock-out).
        order.order_status = "delivered"
        order.save(update_fields=["status", "order_status", "updated_at"])

    from django.urls import reverse
    return JsonResponse({"success": True, "order_id": order.pk,
                         "detail_url": reverse("operating:order_detail", args=[order.pk])})
