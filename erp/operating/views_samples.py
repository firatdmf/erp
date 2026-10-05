"""Sample packages, made and followed from a client's CRM page.

The page's Samples card posts here (crm/components/_samples_card.html).
What a package is, and why it is not an order, is in operating.samples.
"""
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .models import SamplePackage, WarehouseProductItem
from .samples import PackageError, create_package, sample_client, set_package_shipping


@login_required
@require_GET
def sample_roll_search(request):
    """Stock items to put in a package, by barcode, SKU or product name.

    Only items with something left on them. A barcode typed or scanned in
    full comes first, so a scanner's Enter lands on the roll it read.
    """
    query = (request.GET.get("q") or "").strip()
    if len(query) < 2:
        return JsonResponse({"rolls": []})
    rolls = (WarehouseProductItem.objects
             .filter(status__in=("in_stock", "partial"))
             .filter(Q(barcode__icontains=query) | Q(product__sku__icontains=query)
                     | Q(product__name__icontains=query))
             .annotate(exact=Case(When(barcode__iexact=query, then=Value(0)),
                                  default=Value(1), output_field=IntegerField()))
             .select_related("product__warehouse")
             .order_by("exact", "product__name", "id")[:20])
    out = []
    for roll in rolls:
        left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
        if not left or left <= 0:
            continue
        out.append({
            "id": roll.pk,
            "barcode": roll.barcode or "",
            "product": roll.product.name or roll.product.sku or "",
            "sku": roll.product.sku or "",
            "warehouse": roll.product.warehouse.name,
            "left": float(left),
            "unit": roll.product.unit_short,
        })
    return JsonResponse({"rolls": out})


@login_required
@require_POST
def sample_package_create(request):
    """Make a package from the card's form. JSON in, JSON out; all or nothing."""
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"success": False, "error": _("Invalid request.")}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"success": False, "error": _("Invalid request.")}, status=400)

    from accounting.views_purchase import _parse_date

    contact, company = sample_client(data.get("client_type"), data.get("client_pk"))
    try:
        package = create_package(
            contact=contact, company=company,
            lines=data.get("lines") if isinstance(data.get("lines"), list) else [],
            date=_parse_date(data.get("date")),
            note=data.get("note") or "",
            carrier=data.get("carrier") or "",
            tracking_number=data.get("tracking_number") or "",
            sent=bool(data.get("sent")),
            user=request.user,
        )
    except PackageError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": True,
                         "package": {"id": package.pk, "number": package.number}})


@login_required
@require_POST
def sample_package_shipping(request, pk):
    """Record a package's carrier, tracking number and how far it has got."""
    package = get_object_or_404(SamplePackage, pk=pk)
    set_package_shipping(
        package,
        carrier=request.POST.get("carrier") or "",
        tracking_number=request.POST.get("tracking_number") or "",
        status=request.POST.get("status"),
        user=request.user,
    )
    return JsonResponse({"success": True, "status": package.status})
