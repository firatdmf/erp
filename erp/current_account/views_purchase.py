"""
Purchase order views — a warehouse/procurement-flavoured view of the
same underlying data as the Invoice(type="purchase") records (created
by operating.WarehouseManualAdd on stock intake), deliberately NOT the
generic invoice list/detail. Where the invoice pages show accounting
fields (VAT, e-Arşiv, payment allocations…), these show what a buyer
actually wants to see: which supplier, which products, which physical
tops (rolls) arrived, and how much it cost.

    /cari/satin-alma/                → PurchaseOrderList
    /cari/satin-alma/<id>/           → PurchaseOrderDetail
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Invoice, InvoiceItem
from operating.models import StockMovement, WarehouseProduct, WarehouseProductRoll


@method_decorator(login_required, name="dispatch")
class PurchaseOrderList(View):
    template_name = "current_account/purchase_order_list.html"

    def get(self, request):
        qs = (
            Invoice.objects.filter(type="purchase")
            .select_related("cari", "currency")
            .order_by("-date", "-id")
        )

        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(cari__name__icontains=q)

        supplier_id = (request.GET.get("supplier") or "").strip()
        if supplier_id.isdigit():
            qs = qs.filter(cari_id=int(supplier_id))

        status = (request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        invoices = list(qs[:500])
        for inv in invoices:
            inv.item_count = inv.items.count()

        # Batch-resolve each invoice's warehouse (see PurchaseOrderDetail for
        # why this is derivable at all) in ONE query, so the list's quick
        # Edit icon doesn't cost an extra query per row.
        warehouse_by_invoice = {}
        for inv_id, wh_id in (
            WarehouseProductRoll.objects
            .filter(purchase_invoice_item__invoice_id__in=[i.pk for i in invoices])
            .values_list("purchase_invoice_item__invoice_id", "product__warehouse_id")
        ):
            warehouse_by_invoice.setdefault(inv_id, wh_id)
        for inv in invoices:
            inv.warehouse_id_for_edit = warehouse_by_invoice.get(inv.pk)

        totals = qs.aggregate(total_sum=Sum("total"))

        suppliers = (
            Invoice.objects.filter(type="purchase")
            .values("cari_id", "cari__name")
            .distinct()
            .order_by("cari__name")
        )

        return render(request, self.template_name, {
            "invoices": invoices,
            "n": len(invoices),
            "total_sum": totals["total_sum"] or 0,
            "suppliers": suppliers,
            "q": q,
            "filter_supplier": supplier_id,
            "filter_status": status,
            "status_choices": Invoice.STATUS_CHOICES,
        })


@method_decorator(login_required, name="dispatch")
class PurchaseOrderDetail(View):
    template_name = "current_account/purchase_order_detail.html"

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related("cari", "currency", "book"),
            pk=pk, type="purchase",
        )
        items = list(
            invoice.items
            .select_related("product", "variant")
            .prefetch_related(
                Prefetch(
                    "warehouse_rolls",
                    queryset=WarehouseProductRoll.objects.select_related("product", "product__warehouse"),
                )
            )
            .order_by("line_no")
        )
        # Every purchase invoice is intrinsically scoped to ONE warehouse
        # (WarehouseManualAdd only ever intakes into the warehouse pk in its
        # own URL) — derive it from any surviving linked roll so the Edit
        # button knows which warehouse's sidebar to reopen. None means every
        # roll link on this invoice has already been orphaned (e.g. by the
        # generic invoice editor before this dedicated flow existed) — Edit
        # can't be offered, only Cancel (money-only, since there's no stock
        # left to trace back to this invoice).
        warehouse_id = (
            WarehouseProductRoll.objects
            .filter(purchase_invoice_item__invoice_id=invoice.pk)
            .values_list("product__warehouse_id", flat=True)
            .first()
        )
        return render(request, self.template_name, {
            "invoice": invoice,
            "items": items,
            "warehouse_id": warehouse_id,
        })


class PurchaseCancelBlocked(Exception):
    """Raised by cancel_purchase_invoice() when the cancel can't proceed
    because one or more tops are already reserved into a customer order.
    Carries `.blockers` — [{"barcode": ..., "order_ids": [...]}, ...]."""
    def __init__(self, message, blockers=None):
        super().__init__(message)
        self.blockers = blockers or []


def cancel_purchase_invoice(invoice_pk, user):
    """Cancel a purchase invoice: hard-deletes every physical top it
    brought in (after confirming NONE has ever been reserved into a
    customer order — checked and acted on under a row lock in the SAME
    transaction, so a concurrent scan can't slip past the check), then
    cancels the invoice/cari via the existing, unmodified Invoice.cancel().

    Raises PurchaseCancelBlocked (nothing mutated) if any top is reserved,
    or Invoice.DoesNotExist / ValueError if the invoice can't be cancelled.
    Returns the now-cancelled Invoice.

    The ONE place this irreversible operation is implemented — shared by
    PurchaseCancel (the dedicated purchase-page endpoint) and InvoiceCancel
    (the generic invoice page, when reached for a type="purchase" invoice).
    """
    from operating.views_warehouse import _resync_wp_catalog

    with transaction.atomic():
        invoice = (Invoice.objects.select_for_update()
                   .select_related("cari").get(pk=invoice_pk, type="purchase"))
        if invoice.status == "cancelled":
            raise ValueError("Bu alım zaten iptal edilmiş.")

        rolls = list(
            WarehouseProductRoll.objects
            .filter(purchase_invoice_item__invoice=invoice)
            .select_for_update()
            .select_related("product")
        )

        blockers = []
        for roll in rolls:
            if roll.reservations.exists():
                order_ids = list(roll.reservations.values_list("order_id", flat=True).distinct())
                blockers.append({"barcode": roll.barcode, "order_ids": order_ids})
        if blockers:
            raise PurchaseCancelBlocked(
                "Bu alımdaki bazı toplar başka bir siparişte kullanılmış — "
                "önce o siparişi düzeltmeden alım iptal edilemez.",
                blockers,
            )

        touched_wp_ids = set()
        for roll in rolls:
            wp = roll.product
            touched_wp_ids.add(wp.pk)
            StockMovement.objects.create(
                product=wp, roll=None, movement_type="adjustment",
                quantity=-(roll.meters_remaining if roll.meters_remaining is not None else roll.meters),
                reason="Purchase cancelled",
                reference=roll.barcode, created_by=user,
            )
            roll.delete()

        for wp_id in touched_wp_ids:
            wp = WarehouseProduct.objects.filter(pk=wp_id).first()
            if wp is None:
                continue
            total = Decimal("0")
            for r in wp.rolls.all():
                rem = r.meters_remaining if r.meters_remaining is not None else (r.meters or Decimal("0"))
                total += rem or Decimal("0")
            wp.quantity = total
            wp.save(update_fields=["quantity", "updated_at"])
            _resync_wp_catalog(wp)

        invoice.cancel(user=user)
        return invoice


@method_decorator(login_required, name="dispatch")
class PurchaseCancel(View):
    """Cancel a purchase — irreversible: hard-deletes every physical top
    it brought in, then cancels the invoice/cari. Blocked entirely (no
    partial cancel) if ANY of its tops has ever been reserved into a
    customer order.

    Admin-gated like other destructive warehouse actions — this isn't an
    audit-safe reversal like Invoice.cancel() alone; the stock is gone for
    good, and InvoiceRestore refuses to resurrect a purchase invoice for
    exactly that reason.
    """

    def post(self, request, pk):
        from operating.views_warehouse import _is_admin

        if not _is_admin(request.user):
            return JsonResponse({"success": False, "error": "Bu işlem için yönetici yetkisi gerekiyor."}, status=403)

        try:
            invoice = cancel_purchase_invoice(pk, request.user)
        except Invoice.DoesNotExist:
            return JsonResponse({"success": False, "error": "Alım bulunamadı."}, status=404)
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except PurchaseCancelBlocked as exc:
            return JsonResponse({"success": False, "error": str(exc), "blocked": exc.blockers}, status=422)

        return JsonResponse({"success": True, "invoice_id": invoice.pk})
