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
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Invoice, InvoiceItem
from operating.models import WarehouseProductRoll


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
        return render(request, self.template_name, {
            "invoice": invoice,
            "items": items,
        })
