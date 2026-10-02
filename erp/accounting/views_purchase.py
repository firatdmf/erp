"""
Purchase order views — a warehouse/procurement-flavoured view of the
same underlying data as the Invoice(type="purchase") records (created
by operating.WarehouseManualAdd on stock intake), deliberately NOT the
generic invoice list/detail. Where the invoice pages show accounting
fields (VAT, e-Arşiv, payment allocations…), these show what a buyer
actually wants to see: which supplier, which products, which physical
stock items (rolls) arrived, and how much it cost.

    /accounting/accounts/purchases/           → PurchaseOrderList
    /accounting/accounts/purchases/<id>/      → PurchaseOrderDetail
    /accounting/accounts/purchases/new/       → GoodsReceipt (blank)
    /accounting/accounts/purchases/<id>/edit/ → GoodsReceipt (pre-filled)
"""
import copy
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, gettext as _gettext, ngettext
from django.views import View

from .models import CurrencyCategory, Invoice, InvoiceItem
from .models_accounts import CurrentAccount, CurrentAccountSettings
from .purchase_audit import (
    decorate_changes, diff_fields, diff_plans, log_purchase, snapshot_fields,
)
from .services_accounts import (
    _currency_by_code, convert_lines_to_currency, invoice_currency_for,
    mark_as_supplier, MixedCurrencyError,
)
from marketing import units
from marketing.models import (
    Product, ProductVariant, ProductVariantAttribute, ProductVariantAttributeValue,
)


def _fallback_code_prefix():
    """Imported lazily: operating already imports accounting."""
    from operating.views_warehouse import _fallback_prefix
    return _fallback_prefix()

from operating.models import (
    StockMovement, Warehouse, WarehouseProduct, WarehouseProductItem,
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
        # One book's purchases, not every book's. The route is
        # books/<id>/purchases/, so book_scoped has already resolved
        # request.book; without this filter the page listed all 10
        # purchase invoices under whichever book you opened it in and
        # summed their totals into that book's figure — Ergene showing
        # Laleli's suppliers and Laleli's money.
        qs = (
            Invoice.objects.filter(type="purchase", book=request.book)
            .select_related("current_account", "currency", "for_order")
            .order_by("-date", "-id")
        )

        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(current_account__name__icontains=q)

        supplier_id = (request.GET.get("supplier") or "").strip()
        if supplier_id.isdigit():
            qs = qs.filter(current_account_id=int(supplier_id))

        # No status chosen = the live list. A cancelled order is kept
        # for the audit trail, not for reading, so it only shows when
        # asked for by name or through "all"; the total follows the
        # same rule, so a cancelled amount never sits in the sum.
        status = (request.GET.get("status") or "").strip()
        if status == "all":
            pass
        elif status:
            qs = qs.filter(status=status)
        else:
            qs = qs.exclude(status="cancelled")

        invoices = list(qs[:500])
        for inv in invoices:
            inv.item_count = inv.items.count()

        # Batch-resolve each invoice's warehouse (see PurchaseOrderDetail for
        # why this is derivable at all) in ONE query, so the list's quick
        # Edit icon doesn't cost an extra query per row.
        warehouse_by_invoice = {}
        for inv_id, wh_id in (
            WarehouseProductItem.objects
            .filter(purchase_invoice_item__invoice_id__in=[i.pk for i in invoices])
            .values_list("purchase_invoice_item__invoice_id", "product__warehouse_id")
        ):
            warehouse_by_invoice.setdefault(inv_id, wh_id)
        for inv in invoices:
            inv.warehouse_id_for_edit = warehouse_by_invoice.get(inv.pk)

        totals = qs.aggregate(total_sum=Sum("total"))

        # Scoped too: the filter dropdown must not offer a supplier
        # whose invoices this page can never show.
        suppliers = (
            Invoice.objects.filter(type="purchase", book=request.book)
            .values("current_account_id", "current_account__name")
            .distinct()
            .order_by("current_account__name")
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
            Invoice.objects.select_related("current_account", "currency", "book", "intake_warehouse",
                                           "for_order"),
            pk=pk, type="purchase",
        )
        items = list(
            invoice.items
            .select_related("product", "variant__product")
            .prefetch_related(
                Prefetch(
                    "warehouse_stock_items",
                    # The catalog product behind each stock row says what
                    # the row is counted in ("m", "pcs") — fetched with it
                    # so the rolls print their unit without a query each.
                    queryset=WarehouseProductItem.objects.select_related(
                        "product", "product__warehouse", "product__catalog_variant__product"),
                ),
                # The line spells out what was bought — SKU and every
                # attribute behind it — so fetch the values once for the
                # page rather than once per line as the template walks them.
                # Their order is the model's (by attribute name), so every
                # line reads its attributes in the same sequence.
                Prefetch(
                    "variant__product_variant_attribute_values",
                    queryset=ProductVariantAttributeValue.objects.select_related(
                        "product_variant_attribute"),
                ),
            )
            .order_by("line_no")
        )
        # Not received yet, there are no rolls to list — but the order says
        # which it expects, each with the metres the supplier quoted. Shown
        # in their place, marked approximate. Line order matches
        # plan_lines(), which is what built a draft's items.
        planned = []
        if invoice.status == "draft" and invoice.intake_plan:
            planned = plan_lines(invoice.intake_plan)
            if len(planned) != len(items):
                planned = []
        # A line is packed the way its product is: rolls of cloth, boxes of
        # fitted sheets. The page names the stock items by that pack, so a
        # receiver counting boxes is not told to count rolls.
        for i, it in enumerate(items):
            rolls = it.warehouse_stock_items.all()
            plan = planned[i] if planned else None
            it.planned_rolls = plan["rolls"] if plan else []
            it.plan = plan
            # A draft saved before plan_lines() named the product reads just
            # "ecru"; the plan names it now, so the card does too.
            it.title = plan["description"] if plan else it.description
            product = it.product or next(
                (r.product.catalog_product for r in rolls if r.product_id), None)
            pack_type = (product.pack_type if product is not None
                         else (plan and plan["pack_type"]) or units.DEFAULT_PACK)
            it.pack_type = pack_type
            it.unit_short = units.unit_short(it.unit)
            it.pack_count = len(rolls) or len(it.planned_rolls)
            it.pack_one, it.pack_many = units.pack_nouns(pack_type)
            it.pack_noun = units.pack_noun(pack_type, it.pack_count)
        # What the whole delivery comes to in goods, beside what it costs:
        # so many metres on so many rolls. Only a unit every line shares
        # is printed — metres and pieces added together are a bare number
        # — and mixed packs are called the generic "packs". An order still
        # to be received counts the rolls it expects.
        total_quantity = sum((it.quantity or 0) for it in items)
        total_packs = sum(it.pack_count for it in items)
        unit_set = {it.unit for it in items}
        pack_set = {it.pack_type for it in items}
        total_unit = unit_set.pop() if len(unit_set) == 1 else ""
        total_pack_noun = (units.pack_noun(pack_set.pop(), total_packs)
                           if len(pack_set) == 1 else
                           ngettext("pack", "packs", total_packs))
        # The warehouse is recorded on the invoice from the order onward;
        # falling back to the rolls keeps purchases received before that
        # field existed editable. None = no stock left to trace back to this
        # invoice, so Edit can't be offered — only Cancel (money-only).
        warehouse_id = invoice.intake_warehouse_id or purchase_warehouse_id(invoice.pk)
        from operating.order_purchases import purchase_cancel_warning
        return render(request, self.template_name, {
            "invoice": invoice,
            "items": items,
            "total_quantity": total_quantity,
            "total_unit": total_unit,
            "total_packs": total_packs,
            "total_pack_noun": total_pack_noun,
            "warehouse_id": warehouse_id,
            "is_order": invoice.status == "draft",
            "can_confirm": can_confirm_purchase(request.user),
            "changes": decorate_changes(
                list(invoice.change_logs.select_related("created_by"))),
            # Said in the cancel confirmation: what becomes of the
            # customer's order, which turns on whether packing has started.
            "cancel_order_warning": purchase_cancel_warning(invoice),
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
        WarehouseProductItem.objects
        .filter(purchase_invoice_item__invoice_id=invoice_pk)
        .values_list("product__warehouse_id", flat=True)
        .first()
    )


@method_decorator(login_required, name="dispatch")
class PurchaseItemLabels(View):
    """Every roll sticker for ONE purchase line, as a single inline PDF.

    The stickers are made where the goods are: the delivery is entered,
    the rolls are on the bench and the printer is next to it. Sending the
    warehouseman to each product's own page to print its rolls one product
    at a time is the long way round to the same labels, and it loses the
    one grouping that matters at that moment — what arrived on this line.

    Consumed rolls print too, unlike the product page's button: a purchase
    line is a record of what physically arrived, and reprinting the sheet
    for a delivery should give back the sheet that delivery produced.
    """

    def get(self, request, pk, item_pk):
        item = get_object_or_404(
            InvoiceItem.objects.select_related("invoice"),
            pk=item_pk, invoice_id=pk, invoice__type="purchase",
        )
        rolls = list(
            item.warehouse_stock_items
            .select_related("product", "product__warehouse")
            .order_by("id")
        )
        if not rolls:
            raise Http404("This purchase line has no rolls to label.")

        from operating.warehouse_label import inline_pdf_response, labels_pdf_bytes

        invoice = item.invoice
        line = (item.description or "").strip()
        title = f"{_('Roll labels')} — {invoice.display_number}{f' — {line}' if line else ''}"
        pdf = labels_pdf_bytes([(r.product, r) for r in rolls], title=title)
        return inline_pdf_response(pdf, f"rolls-{invoice.display_number}-{item.line_no}")


@method_decorator(login_required, name="dispatch")
class GoodsReceipt(View):
    """"Mal kabul" — the full-page form that receives a delivery into a
    warehouse: it creates the stock (products, variants, physical stock_items)
    AND the supplier purchase invoice in one atomic submit.

    A page rather than the warehouse sidebar it grew out of, because a
    delivery is a document of its own: it is entered from the purchases
    list, it is what a purchase record is made of, and it is long enough
    (several products, each with variants and stock_items) to deserve the room.

    Both modes render the SAME template; the form itself talks to the
    warehouse endpoints that own the write side:
      new  → POST operating:warehouse_manual_add   (warehouse picked here)
      edit → GET/POST operating:warehouse_purchase_edit (warehouse derived)
    """
    template_name = "accounts/goods_receipt_form.html"

    def get(self, request, pk=None):
        from operating.views_warehouse import (
            _account_choices, _pack_type_choices, _product_category_choices,
        )

        # Combined ("ortak") warehouses are browsing views over other
        # warehouses and hold no stock of their own — intake into one is
        # blocked everywhere else too, so they aren't offered here.
        warehouses = Warehouse.objects.exclude(kind="combined").order_by("name")
        for_order = None        # the customer order this purchase is bought for
        invoice = None          # a RECEIVED purchase: edited against the rolls it has
        order = None            # a DRAFT order: nothing received yet, just a plan
        selected_id = None
        # The scoped route (books/<id>/purchases/new/) names a book; the
        # edit route addresses a document instead, and picks its book up
        # from the document below.
        back_url = (reverse("accounts:purchase_order_list",
                            kwargs={"book_id": request.book.pk})
                    if getattr(request, "book", None) else "")

        if pk is not None:
            doc = get_object_or_404(
                Invoice.objects.select_related("current_account", "currency", "intake_warehouse"),
                pk=pk, type="purchase",
            )
            if doc.status == "cancelled":
                messages.warning(request, _("A cancelled purchase can no longer be edited."))
                return redirect("accounts:purchase_order_detail", pk=doc.pk)
            # Editing reaches this view through an object URL, which names
            # no book — the document's own is the right one, and setting it
            # here keeps every book-scoped link on the page pointing at the
            # purchase's book rather than at whatever the editor happens to
            # be working in.
            request.book = doc.book
            back_url = reverse("accounts:purchase_order_detail", args=[doc.pk])

            for_order = doc.for_order
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

        # Only the working book's shelves: a purchase lands in its book's
        # stock, so another book's warehouse is never the right answer here.
        # (Editing set request.book to the document's own book above.)
        if getattr(request, "book", None):
            warehouses = warehouses.filter(accounting_book=request.book)
        warehouses = list(warehouses)

        if pk is not None:
            if selected_id and not any(w.pk == selected_id for w in warehouses):
                # Its warehouse was turned into a combined view, or moved to
                # another book, after intake — still show where it went.
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

        doc = order or invoice
        return render(request, self.template_name, {
            "warehouses": warehouses,
            "selected_warehouse_id": selected_id,
            "edit_invoice": invoice,
            "order_invoice": order,
            "intake_plan": (order.intake_plan or {}) if order else None,
            "for_order": for_order,
            # What an existing customer order's prices are billed in.
            "for_order_currency": (
                for_order.current_account.default_currency.code
                if for_order and for_order.current_account_id
                and for_order.current_account.default_currency_id else ""),
            "can_confirm": can_confirm_purchase(request.user),
            "today": date.today().isoformat(),
            "order_date": (doc.date.isoformat() if doc else date.today().isoformat()),
            "delivery_date": (doc.delivery_date.isoformat()
                              if doc and doc.delivery_date else ""),
            "back_url": back_url,
            # The page's book, same as the warehouses: an account from any
            # other book would be refused on save (_intake_check_book).
            "accounts": _account_choices(getattr(request, "book", None)),
            "product_categories": _product_category_choices(),
            "pack_types": _pack_type_choices(),
            # Every attribute a variant can be described by, for "+ Attribute".
            "variant_attribute_names": list(
                ProductVariantAttribute.objects.order_by("name").values_list("name", flat=True)),
            # For an account created from the account search.
            "currencies": list(CurrencyCategory.objects.order_by("code")
                               .values_list("code", flat=True)),
            # Read off the fields, so the inputs cap exactly where the model does.
            "sku_max_length": Product._meta.get_field("sku").max_length,
            "variant_sku_max_length": ProductVariant._meta.get_field("variant_sku").max_length,
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
    from marketing.models import Product
    from operating.views_warehouse import _row_label

    lines = []
    products = plan.get("products") or []
    # An existing product is counted in its own unit, whatever the card
    # says — the same rule perform_intake() applies at confirm time.
    def existing_id(p_in):
        mp = p_in.get("main_product") or {}
        pid = str(mp.get("id") or "")
        return int(pid) if mp.get("mode") == "existing" and pid.isdigit() else None

    existing = {pk: (unit, title, sku) for pk, unit, title, sku in
                Product.objects
                .filter(pk__in=[i for i in map(existing_id, products) if i])
                .values_list("pk", "unit", "title", "sku")}
    for p_in in products:
        mp = p_in.get("main_product") or {}
        # Plans saved before products had their own unit carry a single
        # batch-wide one instead.
        ex_unit, ex_title, ex_sku = existing.get(existing_id(p_in), (None, None, None))
        unit = (ex_unit or p_in.get("unit") or plan.get("unit") or "mt")[:20]
        # A picked existing product arrives with its title, not a name (the
        # form sends "name" only for a new one), so the line used to read
        # just "ecru". The catalog's own title wins over either.
        base = (ex_title or mp.get("name") or mp.get("title") or "").strip()
        parent_sku = (ex_sku or mp.get("sku") or "").strip()
        for v_in in (p_in.get("variants") or []):
            qty = Decimal("0")
            rolls = []
            for t in (v_in.get("tops") or []):
                try:
                    q = Decimal(str(t.get("qty") or "0").replace(",", "."))
                except (InvalidOperation, ValueError):
                    q = Decimal("0")
                if q > 0:
                    qty += q
                    rolls.append({"quantity": q, "barcode": (t.get("barcode") or "").strip()})
            if qty <= 0:
                continue
            v_name = _row_label(v_in)
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
                # What the order expects to arrive, roll by roll — shown on
                # the draft's page until the real rolls replace it.
                "rolls": rolls,
                "pack_type": p_in.get("pack_type") or "",
                # Named on the draft's card the way a received line's
                # variant names itself: its product, its SKU, its values.
                "parent_sku": parent_sku,
                "sku": (v_in.get("sku") or "").strip(),
                "attributes": [
                    (str(a.get("name") or "").strip(), str(a.get("value") or "").strip())
                    for a in (v_in.get("attributes") or [])
                    if isinstance(a, dict) and str(a.get("value") or "").strip()],
            })
    return lines


def rebuild_draft_items(invoice, lines):
    """Replace a draft's invoice lines with `lines` and re-total it. A
    draft has no rolls pointing at its items, so there is nothing to
    preserve by editing in place."""
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


def rewrite_draft_plan(invoice, plan):
    """Store `plan` on a draft purchase and rebuild its lines from it, the
    way PurchaseOrderSave does — so a change pushed from the customer's
    order (operating.order_purchases.mirror_item_on_purchases) lands
    exactly as a save on the purchase form would."""
    lines = convert_lines_to_currency(
        plan_lines(plan), invoice_currency_for(invoice.current_account),
        rates=plan.get("rates"), on_date=invoice.date,
    )
    invoice.intake_plan = plan
    invoice.save(update_fields=["intake_plan", "updated_at"])
    rebuild_draft_items(invoice, lines)


class _SaveRefused(Exception):
    """Aborts a purchase save — and rolls back what it wrote — with a
    user-facing message."""


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
            return JsonResponse({"success": False, "error": _gettext("Invalid data.")}, status=400)

        wh_id = str(data.get("warehouse_id") or "").strip()
        warehouse = Warehouse.objects.filter(pk=int(wh_id)).first() if wh_id.isdigit() else None
        if warehouse is None:
            return JsonResponse({"success": False, "error": _gettext("Pick a warehouse.")}, status=400)
        if warehouse.is_combined:
            return JsonResponse({"success": False,
                                 "error": _gettext("A combined warehouse is virtual — the order must go to one of its member warehouses.")}, status=400)

        current_account = None
        if str(data.get("current_account_id") or "").isdigit():
            current_account = CurrentAccount.objects.filter(pk=int(data["current_account_id"])).first()
        if current_account is None:
            return JsonResponse(
                {"success": False,
                 "error": _("Pick a current account — the purchase is posted to it.")},
                status=400)

        from operating.order_purchases import (
            CustomerOrderError, parse_customer, plan_variant_skus,
            put_plan_in_catalog, sync_customer_order,
        )
        from operating.views_warehouse import IntakeError, _intake_check_book
        try:
            _intake_check_book(warehouse, current_account)
        except IntakeError as exc:
            return JsonResponse(exc.payload, status=exc.status)
        try:
            customer = parse_customer(data)
        except CustomerOrderError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)

        lines = plan_lines(data)
        if not lines:
            return JsonResponse(
                {"success": False, "error": _gettext("Enter a quantity on at least one product.")}, status=400)

        order_date = _parse_date(data.get("date")) or date.today()
        delivery = _parse_date(data.get("delivery_date"))
        order_warning = None
        try:
            with transaction.atomic():
                if pk is not None:
                    invoice = get_object_or_404(
                        Invoice.objects.select_for_update(), pk=pk, type="purchase")
                    if invoice.status != "draft":
                        return JsonResponse(
                            {"success": False,
                             "error": _gettext("This purchase is confirmed — it can't be edited as an order.")}, status=400)
                else:
                    invoice = Invoice(type="purchase", status="draft")
                # What the purchase said before this save — the log is the
                # difference (purchase_audit).
                before_plan = copy.deepcopy(invoice.intake_plan) if invoice.pk else None
                before_fields = snapshot_fields(invoice)

                # Same rule as the received alım: one currency, the account's
                # own, and any line priced in another restated into it at the
                # rate the order carried. A draft that billed lira as dollars
                # would only be discovered when it was confirmed.
                try:
                    lines = convert_lines_to_currency(
                        lines, invoice_currency_for(current_account),
                        rates=data.get("rates"), on_date=order_date,
                    )
                except MixedCurrencyError as exc:
                    return JsonResponse({"success": False, "error": str(exc)}, status=400)

                invoice.current_account = current_account
                invoice.book = current_account.book
                invoice.currency = _currency_by_code(invoice_currency_for(current_account))
                invoice.date = order_date
                invoice.delivery_date = delivery
                invoice.due_date = order_date + timedelta(days=current_account.payment_term_days or 30)
                invoice.intake_warehouse = warehouse
                previous_skus = plan_variant_skus(invoice.intake_plan)
                invoice.notes = (data.get("notes") or "")[:2000]
                if not invoice.pk:
                    settings_obj = CurrentAccountSettings.for_book(current_account.book)
                    invoice.series = "PUR"
                    invoice.number = settings_obj.next_invoice_number(series="PUR")
                    invoice.created_by = getattr(request.user, "member", None)
                invoice.save()

                # Bought for a customer: the products go in the catalog now, so
                # the customer's order has lines to point at. That rewrites the
                # plan to name them, which is why it is stored only after.
                if customer is not None or invoice.for_order_id:
                    if (invoice.for_order_id and invoice.for_order.current_account_id
                            and invoice.for_order.current_account.book_id
                            != warehouse.accounting_book_id):
                        raise _SaveRefused(_(
                            "This purchase is for an order in another book — "
                            "receive it into a warehouse of that book."))
                    order_lines = put_plan_in_catalog(data)
                    order_warning = sync_customer_order(
                        invoice, customer, order_lines,
                        book=warehouse.accounting_book,
                        member=getattr(request.user, "member", None),
                        previous_skus=previous_skus,
                    )
                invoice.intake_plan = data
                invoice.save(update_fields=["intake_plan", "updated_at"])

                # Rebuilt from the plan every save — a draft has no rolls pointing
                # at its items, so there is nothing to preserve by editing in place.
                rebuild_draft_items(invoice, lines)
                # A draft order is already an intention to buy from them, and it
                # is the account page's own answer to "who do we buy from" that
                # goes stale otherwise.
                mark_as_supplier(current_account)

                if before_plan is None:
                    log_purchase(invoice, "created", user=request.user,
                                 new=(_("for order %(number)s")
                                      % {"number": invoice.for_order.order_number or invoice.for_order.pk}
                                      if invoice.for_order_id else None))
                    diff_plans(invoice, {}, data, user=request.user)
                else:
                    diff_fields(invoice, before_fields, user=request.user)
                    diff_plans(invoice, before_plan, data, user=request.user)
        except (_SaveRefused, CustomerOrderError) as exc:
            # CustomerOrderError reaches here from put_plan_in_catalog — a
            # row with no sale price, refused before the order is touched.
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except IntakeError as exc:
            return JsonResponse(exc.payload, status=exc.status)
        if order_warning:
            messages.warning(request, order_warning)

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
    variants and physical stock items it describes are created, and the order is
    issued so the supplier is owed for them. All of it in ONE transaction,
    so a failure leaves the order exactly as it was, still a draft, still
    confirmable.
    """

    def post(self, request, pk):
        from operating.views_warehouse import (
            IntakeError, announce_order_hold, perform_intake,
        )

        if not can_confirm_purchase(request.user):
            return JsonResponse(
                {"success": False,
                 "error": _gettext("You don't have permission to confirm purchases — ask your manager.")}, status=403)

        invoice = get_object_or_404(Invoice, pk=pk, type="purchase")
        if invoice.status == "cancelled":
            return JsonResponse({"success": False, "error": _gettext("A cancelled purchase can't be confirmed.")}, status=400)
        if invoice.status != "draft":
            return JsonResponse(
                {"success": False, "error": _gettext("This purchase is already confirmed.")}, status=400)
        plan = invoice.intake_plan or {}
        warehouse = invoice.intake_warehouse
        if not plan.get("products") or warehouse is None:
            return JsonResponse(
                {"success": False,
                 "error": _gettext("This order has no goods-receipt details — edit it and save again.")}, status=400)

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
        announce_order_hold(request, result)

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

    A PDF, rendered from the print template the same way the sales order
    is — see erp.pdf_render. The template's own @media print rules hide
    its toolbar, so the supplier's copy carries no Print button.
    """
    template_name = "accounts/purchase_order_print.html"

    def get(self, request, pk):
        from .services_accounts import brand_name_for
        from erp.pdf_render import document_response

        invoice = get_object_or_404(
            Invoice.objects.select_related("current_account", "currency", "book"),
            pk=pk, type="purchase",
        )
        items = list(invoice.items.order_by("line_no"))
        plan = invoice.intake_plan or {}
        # Roll counts come from the plan while the order is still an order,
        # and from the real stock items once it has been received — the document
        # says the same thing either side of confirmation.
        rolls_by_line = {}
        if invoice.status == "draft":
            # Line order matches plan_lines(), which is what built the items.
            line_no = 0
            for p_in in (plan.get("products") or []):
                for v_in in (p_in.get("variants") or []):
                    stock_items = [t for t in (v_in.get("tops") or [])
                            if str(t.get("qty") or "0").strip() not in ("", "0")]
                    if not stock_items:
                        continue
                    line_no += 1
                    rolls_by_line[line_no] = len(stock_items)
        else:
            for it in items:
                rolls_by_line[it.line_no] = it.warehouse_stock_items.count()
        for it in items:
            it.roll_count = rolls_by_line.get(it.line_no, 0)

        return document_response(request, self.template_name, {
            "invoice": invoice,
            "items": items,
            "warehouse": invoice.intake_warehouse,
            "brand_line": brand_name_for(invoice.book),
            "is_order": invoice.status == "draft",
        }, f"purchase_{invoice.display_number}.pdf")


class PurchaseCancelBlocked(Exception):
    """Raised by cancel_purchase_invoice() when the cancel can't proceed
    because one or more stock items are already reserved into a customer order.
    Carries `.blockers` — [{"barcode": ..., "order_ids": [...]}, ...]."""
    def __init__(self, message, blockers=None):
        super().__init__(message)
        self.blockers = blockers or []


def cancel_purchase_invoice(invoice_pk, user, *, origin="purchase", mirror_order=True):
    """Cancel a purchase invoice: hard-deletes every physical stock item it
    brought in (after confirming NONE has ever been reserved into a
    customer order — checked and acted on under a row lock in the SAME
    transaction, so a concurrent scan can't slip past the check), then
    cancels the invoice/current account via Invoice.cancel() (which deletes the
    posted supplier-debt movement and recomputes the balance).

    Raises PurchaseCancelBlocked (nothing mutated) if any stock item is reserved,
    or Invoice.DoesNotExist / ValueError if the invoice can't be cancelled.
    Returns the now-cancelled Invoice.

    The ONE place this irreversible operation is implemented — shared by
    PurchaseCancel (the dedicated purchase-page endpoint) and InvoiceCancel
    (the generic invoice page, when reached for a type="purchase" invoice).
    """
    from operating.views_warehouse import _resync_wp_catalog

    with transaction.atomic():
        invoice = (Invoice.objects.select_for_update()
                   .select_related("current_account").get(pk=invoice_pk, type="purchase"))
        if invoice.status == "cancelled":
            raise ValueError(_gettext("This purchase is already cancelled."))

        rolls = list(
            WarehouseProductItem.objects
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
                _gettext("Some rolls from this purchase are used on another order — the "
                         "purchase can't be cancelled until that order is corrected."),
                blockers,
            )

        touched_wp_ids = set()
        for roll in rolls:
            wp = roll.product
            touched_wp_ids.add(wp.pk)
            StockMovement.objects.create(
                product=wp, stock_item=None, movement_type="adjustment",
                quantity=-(roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity),
                reason="Purchase cancelled",
                reference=roll.barcode, created_by=user,
            )
            roll.delete()

        for wp_id in touched_wp_ids:
            wp = WarehouseProduct.objects.filter(pk=wp_id).first()
            if wp is None:
                continue
            total = Decimal("0")
            for r in wp.stock_items.all():
                rem = r.quantity_remaining if r.quantity_remaining is not None else (r.quantity or Decimal("0"))
                total += rem or Decimal("0")
            wp.quantity = total
            wp.save(update_fields=["quantity", "updated_at"])
            _resync_wp_catalog(wp)

        was = invoice.status
        invoice.cancel(user=user)
        log_purchase(invoice, "status", field="status", old=was, new="cancelled",
                     origin=origin, user=user)
        invoice.order_note = None
        if invoice.for_order_id:
            # The order was raised for these goods: with the purchase
            # gone, the lines it put there go too, and an order left with
            # nothing on it is cancelled along with it. `mirror_order` is
            # False when the ORDER side started this (its lines are
            # already gone, or the order itself is being cancelled).
            if mirror_order:
                from operating.order_purchases import drop_purchase_lines_from_order
                invoice.order_note = drop_purchase_lines_from_order(invoice, user=user)
            # With this purchase gone nothing is on its way for the order,
            # so the bill post_order_movement held back is due like any
            # other open order's — or stays away, if a sibling purchase
            # is still to come.
            from accounting.services_accounts import post_order_movement
            post_order_movement(invoice.for_order,
                                member=getattr(user, "member", None))
        return invoice


@method_decorator(login_required, name="dispatch")
class PurchaseCancel(View):
    """Cancel a purchase — irreversible: hard-deletes every physical stock item
    it brought in, then cancels the invoice/current account. Blocked entirely (no
    partial cancel) if ANY of its stock items has ever been reserved into a
    customer order.

    Admin-gated like other destructive warehouse actions — the stock is
    gone for good, and invoice cancellation is terminal (no restore path
    exists for any cancelled invoice).
    """

    def post(self, request, pk):
        from operating.views_warehouse import _is_admin

        if not _is_admin(request.user):
            return JsonResponse({"success": False, "error": _gettext("This action needs manager permission.")}, status=403)

        try:
            invoice = cancel_purchase_invoice(pk, request.user)
        except Invoice.DoesNotExist:
            return JsonResponse({"success": False, "error": _gettext("Purchase not found.")}, status=404)
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except PurchaseCancelBlocked as exc:
            return JsonResponse({"success": False, "error": str(exc), "blocked": exc.blockers}, status=422)

        # What became of the customer's order — its lines removed, the
        # order cancelled with the purchase, or left alone because it is
        # being packed (drop_purchase_lines_from_order).
        if getattr(invoice, "order_note", None):
            messages.warning(request, invoice.order_note)
        return JsonResponse({"success": True, "invoice_id": invoice.pk})
