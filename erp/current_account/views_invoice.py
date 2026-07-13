"""
Invoice views (Phase 2).

    /cari/fatura/                       → InvoiceList
    /cari/fatura/yeni/                  → InvoiceCreate (with line items)
    /cari/fatura/yeni/?cari=<id>        → InvoiceCreate prefilled for a cari
    /cari/fatura/<id>/                  → InvoiceDetail
    /cari/fatura/<id>/duzenle/          → InvoiceEdit (draft only)
    /cari/fatura/<id>/kes/              → InvoiceIssue
    /cari/fatura/<id>/iptal/            → InvoiceCancel
    /cari/fatura/<id>/geri-al/          → InvoiceRestore
    /cari/fatura/<id>/sil/              → InvoiceDelete (draft only)

The create/edit forms receive line items as JSON in the `items_json` field,
so the dynamic add/remove UX stays simple and reliable.
"""
import hmac
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext as _g
from django.views import View

from accounting.models import CurrencyCategory
from .models import (
    CariAccount,
    CariSettings,
    Invoice,
    InvoiceItem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_decimal(val, default="0"):
    try:
        return Decimal(str(val if val not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _parse_items(items_json):
    """Parse the items_json field. Returns list of dicts; raises ValueError on bad input."""
    if not items_json:
        return []
    try:
        data = json.loads(items_json)
    except json.JSONDecodeError as e:
        raise ValueError(_g("Could not parse items JSON: %(error)s") % {"error": e})
    if not isinstance(data, list):
        raise ValueError(_g("Items must be a list."))
    out = []
    for i, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            continue
        desc = (raw.get("description") or "").strip()
        if not desc:
            continue
        def _to_int(v):
            try:
                return int(v) if v not in (None, "", "null") else None
            except (TypeError, ValueError):
                return None
        out.append({
            "line_no":       i,
            "description":   desc[:300],
            "product_id":    _to_int(raw.get("product_id")),
            "variant_id":    _to_int(raw.get("variant_id")),
            "quantity":      _parse_decimal(raw.get("quantity"), "1"),
            "unit":          (raw.get("unit") or "pcs")[:20],
            "unit_price":    _parse_decimal(raw.get("unit_price")),
            "discount_rate": _parse_decimal(raw.get("discount_rate")),
            "tax_rate":      _parse_decimal(raw.get("tax_rate"), "20"),
        })
    return out


def _filter_invoices(request):
    qs = Invoice.objects.select_related("cari", "book", "currency").all()

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(cari__name__icontains=q)
            | Q(cari__code__icontains=q)
            | Q(notes__icontains=q)
        )

    cari_id = request.GET.get("cari") or ""
    if cari_id.isdigit():
        qs = qs.filter(cari_id=int(cari_id))

    book_id = request.GET.get("book") or ""
    if book_id.isdigit():
        qs = qs.filter(book_id=int(book_id))

    type_ = request.GET.get("type") or ""
    if type_ in dict(Invoice.INVOICE_TYPES):
        qs = qs.filter(type=type_)

    status_ = request.GET.get("status") or ""
    if status_ in dict(Invoice.STATUS_CHOICES):
        qs = qs.filter(status=status_)

    date_from = request.GET.get("date_from") or ""
    date_to   = request.GET.get("date_to") or ""
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    return qs.order_by("-date", "-id")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceList(View):
    template_name = "current_account/invoice_list.html"

    def get(self, request):
        qs = _filter_invoices(request)

        # Stats — exclude cancelled invoices from both the sum and the
        # unpaid balance. They net to zero on the ledger anyway, so
        # showing their amount as "open balance" would be misleading.
        # The count still includes them so the user can see the full
        # list size on the row count.
        active_qs = qs.exclude(status="cancelled")
        totals = qs.aggregate(n=Count("id"))
        active_totals = active_qs.aggregate(
            total_sum=Sum("total"),
            unpaid_sum=Sum("balance"),
        )

        from accounting.models import Book
        ctx = {
            "invoices":    qs[:500],
            "n":           totals["n"] or 0,
            "total_sum":   active_totals["total_sum"]  or Decimal("0.00"),
            "unpaid_sum":  active_totals["unpaid_sum"] or Decimal("0.00"),
            "books":       Book.objects.all(),
            "type_choices":   Invoice.INVOICE_TYPES,
            "status_choices": Invoice.STATUS_CHOICES,
            "q":           request.GET.get("q", ""),
            "filter_book": request.GET.get("book", ""),
            "filter_type": request.GET.get("type", ""),
            "filter_status": request.GET.get("status", ""),
            "filter_cari": request.GET.get("cari", ""),
            "date_from":   request.GET.get("date_from", ""),
            "date_to":     request.GET.get("date_to", ""),
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceCreate(View):
    template_name = "current_account/invoice_form.html"

    def get(self, request):
        prefilled_cari = None
        prefilled_order = None
        items_json = "[]"

        # ── Path A: explicit ?cari=<id> ───────────────────────────
        cari_id = request.GET.get("cari")
        if cari_id and cari_id.isdigit():
            prefilled_cari = CariAccount.objects.filter(pk=int(cari_id)).first()

        # ── Path B: ?order=<id> — pre-fill cari + line items from
        # the operating order so the user can create an invoice
        # straight from the order detail page. The cari comes from
        # the order's auto-linked cari (see operating/views.py).
        order_id = request.GET.get("order")
        if order_id and order_id.isdigit():
            from operating.models import Order
            prefilled_order = (
                Order.objects.select_related("cari")
                .prefetch_related("items__product", "items__product_variant")
                .filter(pk=int(order_id)).first()
            )
            if prefilled_order:
                # An order is only invoiceable once it's actually gone
                # out the door — before that the receivable can still
                # change (or the whole order be cancelled), so the
                # invoice would be fiction.
                from operating.views_warehouse import SHIPPED_CLASS
                if prefilled_order.order_status not in SHIPPED_CLASS:
                    messages.warning(
                        request,
                        _g("An invoice can only be created after the order is completed (shipped)."),
                    )
                    return redirect("operating:order_detail", pk=prefilled_order.pk)
                # Block duplicate invoices — if this order already has a
                # non-cancelled invoice, bounce back to the order detail
                # with an explanatory message. The user must cancel or
                # delete the existing one first.
                existing = prefilled_order.invoices.exclude(status="cancelled").first()
                if existing:
                    messages.warning(
                        request,
                        _g("This order already has an invoice (%(num)s). Cancel or delete it before creating a new one.")
                        % {"num": f"{existing.series}-{existing.number}"},
                    )
                    return redirect("operating:order_detail", pk=prefilled_order.pk)
                if prefilled_order.cari and not prefilled_cari:
                    prefilled_cari = prefilled_order.cari
                # Shape order items into the invoice items_json format
                # expected by _parse_items / the form's JS handler.
                items = []
                for it in prefilled_order.items.all():
                    desc = ""
                    if it.product_variant:
                        desc = f"{it.product.title} [{it.product_variant.variant_sku}]"
                    elif it.product:
                        desc = it.product.title
                    items.append({
                        "description":   desc or "Item",
                        "product_id":    it.product_id,
                        "variant_id":    it.product_variant_id,
                        "quantity":      str(it.quantity or 0),
                        "unit":          "pcs",
                        "unit_price":    str(it.price or 0),
                        "discount_rate": "0",
                        "tax_rate":      "20",
                    })
                import json as _json
                items_json = _json.dumps(items)

        cari_options = (
            CariAccount.objects.filter(is_active=True).order_by("name")
            if not prefilled_cari else CariAccount.objects.none()
        )

        return render(request, self.template_name, {
            "invoice": None,
            "prefilled_cari": prefilled_cari,
            "prefilled_order": prefilled_order,
            "cari_options": cari_options,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices": Invoice.INVOICE_TYPES,
            "default_due_days": 30,
            "items_json": items_json,
        })

    def post(self, request):
        cari_id = request.POST.get("cari")
        if not cari_id:
            messages.error(request, _g("An account must be selected."))
            return redirect("current_account:invoice_create")

        cari = get_object_or_404(CariAccount, pk=int(cari_id))

        # Parse items first — bail early if invalid
        try:
            items_data = _parse_items(request.POST.get("items_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("current_account:invoice_create")
        if not items_data:
            messages.error(request, _g("You must add at least one invoice item."))
            return redirect("current_account:invoice_create")

        invoice_type = request.POST.get("type") or "sales"
        series = request.POST.get("series") or "INV"
        currency_id = int(request.POST.get("currency") or cari.default_currency_id)

        settings_obj = CariSettings.for_book(cari.book)
        number = settings_obj.next_invoice_number(series=series)

        try:
            date = request.POST.get("date") or timezone.now().date().isoformat()
            due_date = request.POST.get("due_date")
            if not due_date:
                # Default to cari payment_term_days
                from datetime import date as _date, timedelta
                d = _date.fromisoformat(date)
                due_date = (d + timedelta(days=cari.payment_term_days)).isoformat()
        except ValueError:
            messages.error(request, _g("Invalid date."))
            return redirect("current_account:invoice_create")

        # If invoice is being created from an operating Order, capture
        # the link so we can pre-fill from it next time and join the
        # invoice to its source order in reports.
        order_obj = None
        order_id = request.POST.get("order")
        if order_id and str(order_id).isdigit():
            from operating.models import Order
            order_obj = Order.objects.filter(pk=int(order_id)).first()
            # Server-side guards — same checks the GET path runs, so a
            # stale form submit can't slip past us.
            if order_obj:
                from operating.views_warehouse import SHIPPED_CLASS
                if order_obj.order_status not in SHIPPED_CLASS:
                    messages.warning(
                        request,
                        _g("An invoice can only be created after the order is completed (shipped)."),
                    )
                    return redirect("operating:order_detail", pk=order_obj.pk)
                dup = order_obj.invoices.exclude(status="cancelled").first()
                if dup:
                    messages.warning(
                        request,
                        _g("This order already has an invoice (%(num)s). Cancel or delete it before creating a new one.")
                        % {"num": f"{dup.series}-{dup.number}"},
                    )
                    return redirect("operating:order_detail", pk=order_obj.pk)

        # Per-invoice consignee/issuer overrides (blank = use cari/brand)
        snapshot = {
            "bill_to_name":       (request.POST.get("bill_to_name") or "").strip(),
            "bill_to_address":    (request.POST.get("bill_to_address") or "").strip(),
            "bill_to_city":       (request.POST.get("bill_to_city") or "").strip(),
            "bill_to_country":    (request.POST.get("bill_to_country") or "").strip(),
            "bill_to_phone":      (request.POST.get("bill_to_phone") or "").strip(),
            "bill_to_email":      (request.POST.get("bill_to_email") or "").strip(),
            "bill_to_tax_office": (request.POST.get("bill_to_tax_office") or "").strip(),
            "bill_to_tax_number": (request.POST.get("bill_to_tax_number") or "").strip(),
            "issuer_name":        (request.POST.get("issuer_name") or "").strip(),
            "issuer_address":     (request.POST.get("issuer_address") or "").strip(),
            "issuer_phone":       (request.POST.get("issuer_phone") or "").strip(),
            "issuer_fax":         (request.POST.get("issuer_fax") or "").strip(),
            "issuer_email":       (request.POST.get("issuer_email") or "").strip(),
            "issuer_tax_office":  (request.POST.get("issuer_tax_office") or "").strip(),
            "issuer_tax_number":  (request.POST.get("issuer_tax_number") or "").strip(),
        }

        with transaction.atomic():
            invoice = Invoice.objects.create(
                cari=cari,
                book=cari.book,
                series=series,
                number=number,
                type=invoice_type,
                status="draft",
                date=date,
                due_date=due_date,
                delivery_date=request.POST.get("delivery_date") or None,
                currency_id=currency_id,
                other_charges=_parse_decimal(request.POST.get("other_charges")),
                notes=request.POST.get("notes", ""),
                order=order_obj,
                created_by=getattr(request.user, "member", None),
                **snapshot,
            )
            for item in items_data:
                InvoiceItem.objects.create(invoice=invoice, **item)
            invoice.recompute_totals(save=True)

            # Auto-issue if requested
            if request.POST.get("auto_issue") == "1":
                try:
                    invoice.issue(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Invoice created but could not be issued: %(error)s") % {"error": ve})

        messages.success(request, _g("Invoice created: %(series)s-%(number)s") % {"series": invoice.series, "number": invoice.number})
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Edit
#   - Draft   → freely editable (no ledger movement yet)
#   - Issued / Partially Paid / Paid / Overdue → editable; on save we
#     refresh the linked CariMovement (description, date, due, amount)
#     so the cari ledger stays in lock-step with the invoice. The
#     amount-zero rule for order-attached invoices still applies, so
#     edits to such invoices NEVER touch the balance.
#   - Cancelled → not editable; the cancellation counter-movement
#     already balanced the ledger, and changing the original would
#     drift things out of sync.
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceEdit(View):
    template_name = "current_account/invoice_form.html"

    def _block_if_cancelled(self, request, invoice):
        if invoice.status == "cancelled":
            messages.warning(request, _g("Cancelled invoices can't be edited. Create a new one if needed."))
            return redirect("current_account:invoice_detail", pk=invoice.pk)
        return None

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        blocked = self._block_if_cancelled(request, invoice)
        if blocked:
            return blocked

        return render(request, self.template_name, {
            "invoice": invoice,
            "prefilled_cari": invoice.cari,
            "currencies": CurrencyCategory.objects.all().order_by("code"),
            "type_choices": Invoice.INVOICE_TYPES,
            "items_json": json.dumps([{
                "description":   it.description,
                "product_id":    it.product_id,
                "variant_id":    it.variant_id,
                "quantity":      str(it.quantity),
                "unit":          it.unit,
                "unit_price":    str(it.unit_price),
                "discount_rate": str(it.discount_rate),
                "tax_rate":      str(it.tax_rate),
            } for it in invoice.items.order_by("line_no")]),
        })

    def post(self, request, pk):
        from decimal import Decimal
        invoice = get_object_or_404(Invoice, pk=pk)
        blocked = self._block_if_cancelled(request, invoice)
        if blocked:
            return blocked

        try:
            items_data = _parse_items(request.POST.get("items_json", ""))
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("current_account:invoice_edit", pk=pk)
        if not items_data:
            messages.error(request, _g("You must add at least one invoice item."))
            return redirect("current_account:invoice_edit", pk=pk)

        with transaction.atomic():
            invoice.type = request.POST.get("type") or invoice.type
            invoice.date = request.POST.get("date") or invoice.date
            invoice.due_date = request.POST.get("due_date") or invoice.due_date
            invoice.delivery_date = request.POST.get("delivery_date") or None
            currency_id = request.POST.get("currency")
            if currency_id:
                invoice.currency_id = int(currency_id)
            invoice.other_charges = _parse_decimal(request.POST.get("other_charges"))
            invoice.notes = request.POST.get("notes", "")
            # Per-invoice consignee + issuer overrides
            for f in ("bill_to_name", "bill_to_address", "bill_to_city", "bill_to_country",
                      "bill_to_phone", "bill_to_email", "bill_to_tax_office", "bill_to_tax_number",
                      "issuer_name", "issuer_address", "issuer_phone", "issuer_fax",
                      "issuer_email", "issuer_tax_office", "issuer_tax_number"):
                setattr(invoice, f, (request.POST.get(f) or "").strip())
            invoice.save()

            # Wipe + recreate items. For issued invoices this is also
            # safe because each InvoiceItem doesn't carry external
            # references — only the parent Invoice + its posted_movement
            # do, which we update next.
            invoice.items.all().delete()
            for item in items_data:
                InvoiceItem.objects.create(invoice=invoice, **item)
            invoice.recompute_totals(save=True)

            # ── Sync the cari movement if this invoice was already
            # posted to the ledger. Order-attached invoices stay at
            # amount=0 (no double counting); standalone invoices get
            # their amount/desc/date refreshed in place.
            mv = invoice.posted_movement
            if mv:
                if invoice.order_id:
                    new_amount = Decimal("0.00")
                else:
                    new_amount = invoice.total * Decimal(invoice.ledger_sign)
                mv.amount = new_amount
                mv.amount_base = Decimal("0")    # force recompute on save
                mv.date = invoice.date
                mv.due_date = invoice.due_date
                mv.currency = invoice.currency
                mv.description = f"{invoice.get_type_display()} {invoice.series}-{invoice.number}"
                mv.reference = f"{invoice.series}-{invoice.number}"
                mv.save()
                # CariMovement.save() already calls recompute_balance,
                # so the cari snapshot is up-to-date now.

            if request.POST.get("auto_issue") == "1" and invoice.status == "draft":
                try:
                    invoice.issue(user=request.user)
                except ValidationError as ve:
                    messages.warning(request, _g("Edited but could not be issued: %(error)s") % {"error": ve})

        messages.success(request, _g("Invoice updated."))
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceDetail(View):
    template_name = "current_account/invoice_detail.html"

    def get(self, request, pk):
        from django.db.models import Prefetch
        from operating.models import WarehouseProductRoll

        invoice = get_object_or_404(
            Invoice.objects.select_related("cari", "book", "currency", "order",
                                           "posted_movement"),
            pk=pk,
        )
        # Roll-level traceability — "which physical tops" per line, for
        # both directions: purchase invoices link rolls directly
        # (purchase_invoice_item), sales invoices via the order line's
        # consumed reservations (order_item -> roll_reservations).
        items = list(invoice.items.select_related(
            "product", "product__category", "variant",
        ).prefetch_related(
            Prefetch("warehouse_rolls",
                     queryset=WarehouseProductRoll.objects.select_related("product")),
            "order_item__roll_reservations__roll",
        ).order_by("line_no"))
        for it in items:
            purchase_rolls = list(it.warehouse_rolls.all())
            if purchase_rolls:
                # Each roll here IS the physical top this PO line put
                # into stock — its own .meters is exactly that line's
                # contribution, safe to show as-is.
                it.display_rolls = [
                    {"barcode": r.barcode, "meters": r.meters} for r in purchase_rolls
                ]
            elif it.order_item_id:
                # A roll can be shared across order lines (partial
                # cuts) — the reservation's own .meters is what THIS
                # line actually used, not the roll's full size.
                it.display_rolls = [
                    {"barcode": r.roll.barcode, "meters": r.meters}
                    for r in it.order_item.roll_reservations.all() if r.consumed
                ]
            else:
                it.display_rolls = []

        # Tax breakdown by rate (for the totals summary)
        tax_breakdown = {}
        for it in items:
            key = str(it.tax_rate)
            agg = tax_breakdown.setdefault(key, {"net": Decimal("0"), "tax": Decimal("0")})
            agg["net"] += (it.subtotal - it.discount_amount)
            agg["tax"] += it.tax_amount

        return render(request, self.template_name, {
            "invoice": invoice,
            "items":   items,
            "tax_breakdown": sorted(tax_breakdown.items()),
        })


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceIssue(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            invoice.issue(user=request.user)
            messages.success(request, _g("Invoice issued: %(series)s-%(number)s") % {"series": invoice.series, "number": invoice.number})
        except ValidationError as ve:
            messages.error(request, _g("Issue failed: %(error)s") % {"error": ve})
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceCancel(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        reason = request.POST.get("reason", "")
        invoice.cancel(user=request.user, reason=reason)
        messages.success(request, _g("Invoice cancelled."))

        # Invoice and order live or die together: cancelling the invoice
        # cancels its source order too, which reverses the order_sale
        # movement off the cari and (if it was shipped) restores the cut
        # stock — all via the single status funnel so nothing diverges.
        if invoice.order_id:
            order = invoice.order
            if order.order_status != "cancelled":
                from operating.views_warehouse import apply_order_status_change
                ok, code = apply_order_status_change(order, "cancelled", user=request.user)
                if ok:
                    messages.success(
                        request,
                        _g("Linked order #%(num)s was cancelled as well — its cari posting was reversed and any shipped stock restored.")
                        % {"num": order.pk},
                    )
                else:
                    messages.warning(
                        request,
                        _g("Invoice cancelled, but the linked order #%(num)s could not be cancelled automatically (%(code)s).")
                        % {"num": order.pk, "code": code or ""},
                    )
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Restore (undo cancel)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceRestore(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status != "cancelled":
            messages.error(request, _g("Only cancelled invoices can be restored."))
            return redirect("current_account:invoice_detail", pk=invoice.pk)

        password = request.POST.get("password", "")
        if not hmac.compare_digest(password, settings.INVOICE_RESTORE_PASSWORD):
            messages.error(request, _g("Incorrect password. Invoice was not restored."))
            return redirect("current_account:invoice_detail", pk=invoice.pk)

        if invoice.order_id:
            dup = invoice.order.invoices.exclude(status="cancelled").exclude(pk=invoice.pk).first()
            if dup:
                messages.warning(
                    request,
                    _g("This order already has an active invoice (%(num)s). Cancel or delete it before restoring this one.")
                    % {"num": f"{dup.series}-{dup.number}"},
                )
                return redirect("current_account:invoice_detail", pk=invoice.pk)

        reason = request.POST.get("reason", "")
        invoice.restore(user=request.user, reason=reason)
        messages.success(request, _g("Invoice restored."))
        return redirect("current_account:invoice_detail", pk=invoice.pk)


# ---------------------------------------------------------------------------
# Delete (draft only)
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class InvoiceDelete(View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status != "draft":
            messages.error(request, _g("Only draft invoices can be deleted. Cancel issued invoices instead."))
            return redirect("current_account:invoice_detail", pk=invoice.pk)
        label = f"{invoice.series}-{invoice.number}"
        invoice.delete()
        messages.success(request, _g("Draft invoice deleted: %(label)s") % {"label": label})
        return redirect("current_account:invoice_list")
