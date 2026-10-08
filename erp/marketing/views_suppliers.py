"""The Suppliers card on a catalog product's page: who sells each of its
variants, what they call it, and what they last charged.

Rows are written by purchases (marketing.supplier_items); this is where
one is put right afterwards — a code typed against the wrong variant has
to be taken off it before the purchase page will accept it on the right
one, since one of a supplier's codes means one of our variants.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import SupplierItem
from .supplier_items import SupplierSkuTaken, set_code


def supplier_rows(product, member):
    """The product's supplier entries the reader may see: an account lives
    in a book, and another book's suppliers and prices are not theirs."""
    from accounting.services_accounts import member_books
    return list(
        SupplierItem.objects
        .filter(variant__product=product,
                current_account__book__in=member_books(member))
        .select_related("variant", "current_account")
        .order_by("variant__variant_sku", "-is_preferred", "current_account__name"))


@login_required
@require_POST
def supplier_item_update(request, pk):
    """POST JSON {supplier_sku} to correct their code, {remove: true} to
    forget that they sell the variant at all."""
    from accounting.services_accounts import member_books
    item = get_object_or_404(
        SupplierItem.objects.select_related("current_account", "variant"),
        pk=pk, current_account__book__in=member_books(getattr(request.user, "member", None)))
    try:
        data = json.loads((request.body or b"").decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": _("Invalid data.")}, status=400)

    if data.get("remove"):
        item.delete()
        return JsonResponse({"success": True, "removed": True})
    try:
        set_code(item, data.get("supplier_sku"))
    except SupplierSkuTaken as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=409)
    return JsonResponse({"success": True, "supplier_sku": item.supplier_sku})
