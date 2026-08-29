"""
Purchase order views — a warehouse/procurement-flavoured view of the
same underlying data as the Invoice(type="purchase") records (created
by operating.WarehouseManualAdd on stock intake), deliberately NOT the
generic invoice list/detail. Where the invoice pages show accounting
fields (VAT, e-Arşiv, payment allocations…), these show what a buyer
actually wants to see: which supplier, which products, which physical
tops (rolls) arrived, and how much it cost.

    /accounting/accounts/purchases/           → PurchaseOrderList
    /accounting/accounts/purchases/<id>/      → PurchaseOrderDetail
    /accounting/accounts/purchases/new/       → GoodsReceipt (blank)
    /accounting/accounts/purchases/<id>/edit/ → GoodsReceipt (pre-filled)
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View

from .models import Invoice, InvoiceItem
from .models_accounts import CariAccount, CariSettings
from .services_accounts import _currency_by_code, mark_as_supplier
from marketing.models import SKU_MAX_LENGTH


def _fallback_code_prefix():
    """Imported lazily: operating already imports accounting."""
    from operating.views_warehouse import _fallback_prefix
    return _fallback_prefix()

from operating.models import (
    StockMovement, Warehouse, WarehouseProduct, WarehouseProductRoll,
)


def _parse_date(value):
    """A yyyy-mm-dd string from the form, or None."""
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@method_decorator(login_required, name="dispatch")
class PurchaseOrderList(View):
    template_name = "accounts/purchase_order_list.html"

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
    template_name = "accounts/purchase_order_detail.html"

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related("cari", "currency", "book", "intake_warehouse"),
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
        # The warehouse is recorded on the invoice from the order onward;
        # falling back to the rolls keeps purchases received before that
        # field existed editable. None = no stock left to trace back to this
        # invoice, so Edit can't be offered — only Cancel (money-only).
        warehouse_id = invoice.intake_warehouse_id or purchase_warehouse_id(invoice.pk)
        return render(request, self.template_name, {
            "invoice": invoice,
            "items": items,
            "warehouse_id": warehouse_id,
            "is_order": invoice.status == "draft",
            "can_confirm": can_confirm_purchase(request.user),
        })


def purchase_warehouse_id(invoice_pk):
    """The ONE warehouse a purchase belongs to, or None.

    Every purchase invoice is intrinsically scoped to a single warehouse
    (intake only ever writes into the warehouse whose pk is in its own
    URL), so it is derivable from any surviving linked roll. None means
    every roll link on this invoice has been orphaned (e.g. by the generic
    invoice editor before the dedicated flow existed) — such a purchase
    can no longer be edited, only viewed or cancelled.
    """
    return (
        WarehouseProductRoll.objects
        .filter(purchase_invoice_item__invoice_id=invoice_pk)
        .values_list("product__warehouse_id", flat=True)
        .first()
    )


@method_decorator(login_required, name="dispatch")
class GoodsReceipt(View):
    """"Mal kabul" — the full-page form that receives a delivery into a
    warehouse: it creates the stock (products, variants, physical tops)
    AND the supplier purchase invoice in one atomic submit.

    A page rather than the warehouse sidebar it grew out of, because a
    delivery is a document of its own: it is entered from the purchases
    list, it is what a purchase record is made of, and it is long enough
    (several products, each with variants and tops) to deserve the room.

    Both modes render the SAME template; the form itself talks to the
    warehouse endpoints that own the write side:
      new  → POST operating:warehouse_manual_add   (warehouse picked here)
      edit → GET/POST operating:warehouse_purchase_edit (warehouse derived)
    """
    template_name = "accounts/goods_receipt_form.html"

    def get(self, request, pk=None):
        from operating.views_warehouse import (
            _account_choices, _product_category_choices,
        )

        # Combined ("ortak") warehouses are browsing views over other
        # warehouses and hold no stock of their own — intake into one is
        # blocked everywhere else too, so they aren't offered here.
        warehouses = list(Warehouse.objects.exclude(kind="combined").order_by("name"))
        invoice = None          # an ISSUED purchase: rolls exist, identity locked
        order = None            # a DRAFT order: nothing received yet, fully editable
        selected_id = None
        back_url = reverse("accounts:purchase_order_list")

        if pk is not None:
            doc = get_object_or_404(
                Invoice.objects.select_related("cari", "currency", "intake_warehouse"),
                pk=pk, type="purchase",
            )
            if doc.status == "cancelled":
                messages.warning(request, _("A cancelled purchase can no longer be edited."))
                return redirect("accounts:purchase_order_detail", pk=doc.pk)
            back_url = reverse("accounts:purchase_order_detail", args=[doc.pk])

            if doc.status == "draft":
                # Still an order — it owns a plan, not stock, so the form
                # opens the way it was left and everything stays editable.
                order = doc
                selected_id = doc.intake_warehouse_id
            else:
                invoice = doc
                selected_id = doc.intake_warehouse_id or purchase_warehouse_id(doc.pk)
                if not selected_id:
                    messages.warning(
                        request,
                        _("This purchase's stock links are missing, so it can't be edited — "
                          "view or cancel it from the purchases page instead."),
                    )
                    return redirect("accounts:purchase_order_detail", pk=doc.pk)
            if selected_id and not any(w.pk == selected_id for w in warehouses):
                # Its warehouse was turned into a combined view after intake.
                w = Warehouse.objects.filter(pk=selected_id).first()
                if w:
                    warehouses.append(w)
        else:
            asked = (request.GET.get("warehouse") or "").strip()
            if asked.isdigit() and any(w.pk == int(asked) for w in warehouses):
                selected_id = int(asked)
                back_url = reverse("operating:warehouse_detail", args=[selected_id])
            elif len(warehouses) == 1:
                # Nothing to choose between — don't make it a decision.
                selected_id = warehouses[0].pk

        return render(request, self.template_name, {
            "warehouses": warehouses,
            "selected_warehouse_id": selected_id,
            "edit_invoice": invoice,
            "order_invoice": order,
            "intake_plan": (order.intake_plan or {}) if order else None,
            "can_confirm": can_confirm_purchase(request.user),
            "today": date.today().isoformat(),
            "order_date": (order.date.isoformat() if order else date.today().isoformat()),
            "delivery_date": (order.delivery_date.isoformat()
                              if order and order.delivery_date else ""),
            "back_url": back_url,
            "accounts": _account_choices(),
            "product_categories": _product_category_choices(),
            "sku_max_length": SKU_MAX_LENGTH,
            # The house's own code, so the SKU the page previews for an
            # account with no consonants to abbreviate is the one the save
            # actually mints — see views_warehouse._fallback_prefix.
            "code_prefix": _fallback_code_prefix(),
        })


def can_confirm_purchase(user):
    """Who may turn a purchase ORDER into stock.

    Confirming writes real inventory AND posts what we owe the supplier, so
    it is held apart from merely writing the order down (which anyone who
    can log in may do). Admins always may; anyone else needs the
    "purchase_confirm" permission on their Member, granted from Django
    admin → Members.
    """
    from operating.views_warehouse import _is_admin

    if _is_admin(user):
        return True
    try:
        return user.member.permissions.filter(name="purchase_confirm").exists()
    except Exception:
        return False


def plan_lines(plan):
    """The invoice lines a saved (not yet received) order shows.

    One line per variant, quantity summed over its rolls — the same shape
    perform_intake() will build at confirm time, so the draft's totals are
    what the goods receipt will actually post. Nothing here touches the
    catalog or the warehouse: an order that is still an order must leave no
    trace outside its own document.
    """
    lines = []
    unit = (plan.get("unit") or "mt")[:20]
    for p_in in (plan.get("products") or []):
        mp = p_in.get("main_product") or {}
        base = (mp.get("name") or "").strip()
        for v_in in (p_in.get("variants") or []):
            qty = Decimal("0")
            for t in (v_in.get("tops") or []):
                try:
                    q = Decimal(str(t.get("qty") or "0").replace(",", "."))
                except (InvalidOperation, ValueError):
                    q = Decimal("0")
                if q > 0:
                    qty += q
            if qty <= 0:
                continue
            v_name = (v_in.get("name") or "").strip()
            try:
                price = Decimal(str(v_in.get("price") or "0").replace(",", "."))
            except (InvalidOperation, ValueError):
                price = Decimal("0")
            lines.append({
                "description": (f"{base} {v_name}".strip() or v_in.get("sku") or base)[:300],
                "quantity": qty,
                "unit": unit,
                "unit_price": price,
                "currency": v_in.get("currency") or "USD",
                "product": None,
                "variant": None,
            })
    return lines


@method_decorator(login_required, name="dispatch")
class PurchaseOrderSave(View):
    """Save a purchase as an ORDER — a draft that has NOT reached the
    warehouse. No stock, no catalog rows, no debt: just the document and the
    plan it will be received from, so it stays fully editable until someone
    confirms it.

    POST (no pk) → create; POST /<pk>/save/ → replace an existing draft.
    Body is the goods-receipt payload plus warehouse_id and the two dates.
    """

    def post(self, request, pk=None):
        try:
            data = json.loads((request.body or b"").decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"success": False, "error": "Geçersiz veri."}, status=400)

        wh_id = str(data.get("warehouse_id") or "").strip()
        warehouse = Warehouse.objects.filter(pk=int(wh_id)).first() if wh_id.isdigit() else None
        if warehouse is None:
            return JsonResponse({"success": False, "error": "Depo seçin."}, status=400)
        if warehouse.is_combined:
            return JsonResponse({"success": False,
                                 "error": "Ortak depo sanaldır — sipariş üye depolardan birine yapılmalı."}, status=400)

        cari = None
        if str(data.get("cari_id") or "").isdigit():
            cari = CariAccount.objects.filter(pk=int(data["cari_id"])).first()
        if cari is None:
            return JsonResponse(
                {"success": False, "error": "Cari hesap seçin — alım bu hesaba işlenir."}, status=400)

        lines = plan_lines(data)
        if not lines:
            return JsonResponse(
                {"success": False, "error": "En az bir üründe miktar girin."}, status=400)

        order_date = _parse_date(data.get("date")) or date.today()
        delivery = _parse_date(data.get("delivery_date"))

        with transaction.atomic():
            if pk is not None:
                invoice = get_object_or_404(
                    Invoice.objects.select_for_update(), pk=pk, type="purchase")
                if invoice.status != "draft":
                    return JsonResponse(
                        {"success": False,
                         "error": "Bu alım onaylanmış — sipariş olarak düzenlenemez."}, status=400)
            else:
                invoice = Invoice(type="purchase", status="draft")

            invoice.cari = cari
            invoice.book = cari.book
            invoice.currency = _currency_by_code(lines[0]["currency"])
            invoice.date = order_date
            invoice.delivery_date = delivery
            invoice.due_date = order_date + timedelta(days=cari.payment_term_days or 30)
            invoice.intake_warehouse = warehouse
            invoice.intake_plan = data
            invoice.notes = (data.get("notes") or "")[:2000]
            if not invoice.pk:
                settings_obj = CariSettings.for_book(cari.book)
                invoice.series = "PUR"
                invoice.number = settings_obj.next_invoice_number(series="PUR")
                invoice.created_by = getattr(request.user, "member", None)
            invoice.save()

            # Rebuilt from the plan every save — a draft has no rolls pointing
            # at its items, so there is nothing to preserve by editing in place.
            invoice.items.all().delete()
            for i, line in enumerate(lines, start=1):
                InvoiceItem.objects.create(
                    invoice=invoice, line_no=i,
                    description=line["description"], quantity=line["quantity"],
                    unit=line["unit"], unit_price=line["unit_price"],
                    discount_rate=Decimal("0"), tax_rate=Decimal("0"),
                )
            invoice.recompute_totals(save=True)
            invoice.refresh_from_db()
            # A draft order is already an intention to buy from them, and it
            # is the account page's own answer to "who do we buy from" that
            # goes stale otherwise.
            mark_as_supplier(cari)

        return JsonResponse({
            "success": True,
            "invoice_id": invoice.pk,
            "number": invoice.display_number,
            "detail_url": reverse("accounts:purchase_order_detail", args=[invoice.pk]),
        })


@method_decorator(login_required, name="dispatch")
class PurchaseOrderConfirm(View):
    """Confirm an order: receive it into the warehouse.

    This is the moment the document stops being a plan — the products,
    variants and physical tops it describes are created, and the order is
    issued so the supplier is owed for them. All of it in ONE transaction,
    so a failure leaves the order exactly as it was, still a draft, still
    confirmable.
    """

    def post(self, request, pk):
        from operating.views_warehouse import IntakeError, perform_intake

        if not can_confirm_purchase(request.user):
            return JsonResponse(
                {"success": False,
                 "error": "Alım onaylama yetkiniz yok — yöneticinize başvurun."}, status=403)

        invoice = get_object_or_404(Invoice, pk=pk, type="purchase")
        if invoice.status == "cancelled":
            return JsonResponse({"success": False, "error": "İptal edilmiş alım onaylanamaz."}, status=400)
        if invoice.status != "draft":
            return JsonResponse(
                {"success": False, "error": "Bu alım zaten onaylanmış."}, status=400)
        plan = invoice.intake_plan or {}
        warehouse = invoice.intake_warehouse
        if not plan.get("products") or warehouse is None:
            return JsonResponse(
                {"success": False,
                 "error": "Bu siparişte mal kabul bilgisi yok — düzenleyip tekrar kaydedin."}, status=400)

        try:
            with transaction.atomic():
                result = perform_intake(
                    warehouse, plan,
                    user=request.user if request.user.is_authenticated else None,
                    member=getattr(request.user, "member", None),
                    invoice=invoice,
                )
        except IntakeError as exc:
            return JsonResponse(exc.payload, status=exc.status)

        return JsonResponse({
            "success": True,
            "invoice_id": invoice.pk,
            "created": result["created"],
            "warnings": result["warnings"],
            "detail_url": reverse("accounts:purchase_order_detail", args=[invoice.pk]),
        })


@method_decorator(login_required, name="dispatch")
class PurchaseOrderPrint(View):
    """The order as a document the supplier can be sent.

    Styled HTML the BROWSER prints (and "Save as PDF"), matching how the
    sales order prints — same reason: xhtml2pdf can't reproduce this layout,
    the browser can.
    """
    template_name = "accounts/purchase_order_print.html"

    def get(self, request, pk):
        from .services_accounts import brand_name_for

        invoice = get_object_or_404(
            Invoice.objects.select_related("cari", "currency", "book"),
            pk=pk, type="purchase",
        )
        items = list(invoice.items.order_by("line_no"))
        plan = invoice.intake_plan or {}
        # Roll counts come from the plan while the order is still an order,
        # and from the real tops once it has been received — the document
        # says the same thing either side of confirmation.
        rolls_by_line = {}
        if invoice.status == "draft":
            # Line order matches plan_lines(), which is what built the items.
            line_no = 0
            for p_in in (plan.get("products") or []):
                for v_in in (p_in.get("variants") or []):
                    tops = [t for t in (v_in.get("tops") or [])
                            if str(t.get("qty") or "0").strip() not in ("", "0")]
                    if not tops:
                        continue
                    line_no += 1
                    rolls_by_line[line_no] = len(tops)
        else:
            for it in items:
                rolls_by_line[it.line_no] = it.warehouse_rolls.count()
        for it in items:
            it.roll_count = rolls_by_line.get(it.line_no, 0)

        return render(request, self.template_name, {
            "invoice": invoice,
            "items": items,
            "warehouse": invoice.intake_warehouse,
            "brand_line": brand_name_for(invoice.book),
            "is_order": invoice.status == "draft",
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
    cancels the invoice/cari via Invoice.cancel() (which deletes the
    posted supplier-debt movement and recomputes the balance).

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

    Admin-gated like other destructive warehouse actions — the stock is
    gone for good, and invoice cancellation is terminal (no restore path
    exists for any cancelled invoice).
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
