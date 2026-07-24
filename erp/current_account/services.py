"""Cari account service helpers — keep view code thin and signals clean.

The big picture:
- Every Order placed manually (B2B contact/company) should land on the
  customer's cari. If the contact belongs to a company we always book
  the order against the COMPANY so the company sees one consolidated
  cari (the user explicitly asked for this).
- Web orders skip this entirely (they go through create_web_order
  which is not wired to call into here).
- Each call site is responsible for invoking ensure_cari_for_order +
  post_order_movement once on creation; subsequent edits update or
  re-create the movement.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from accounting.models import Book, CurrencyCategory

from .models import CariAccount, CariMovement, CariSettings


# ---------------------------------------------------------------------------
# Book — the user wants a single shared book; no UI for selecting one.
# ---------------------------------------------------------------------------
def get_default_book() -> Book:
    """Return the singleton default Book, creating one if none exists.

    User constraint: the project has *one* book company-wide. We don't
    expose Book selection in cari/order UI any more. Picking the
    lowest-id row gives us deterministic behaviour even if multiple
    rows happen to exist in legacy data.
    """
    book = Book.objects.order_by("id").first()
    if book:
        return book
    return Book.objects.create(name="Main Book")


def _resolve_currency(order=None) -> CurrencyCategory:
    """Pick a CurrencyCategory for new movements/cari accounts.

    Order doesn't have a currency field — orders are stored in USD by
    convention (per the rest of the codebase). Fall back to whichever
    currency is marked "USD"/base, or the first row.
    """
    base_code = "USD"
    cur = CurrencyCategory.objects.filter(code=base_code).first()
    if cur:
        return cur
    cur = CurrencyCategory.objects.filter(is_base_currency=True).first() \
        if hasattr(CurrencyCategory, "is_base_currency") else None
    return cur or CurrencyCategory.objects.first()


# ---------------------------------------------------------------------------
# Cari resolution
# ---------------------------------------------------------------------------
def get_or_create_cari_for_order(order, *, member=None) -> CariAccount | None:
    """Find (or create) the cari for an order's customer.

    Resolution priority (per user spec):
      1. If the order's contact is tied to a company → use COMPANY's cari.
      2. Else if order.company → use that.
      3. Else if order.contact → use contact's cari.
      4. Else → return None (web_client / no customer = skip).

    The CariAccount unique-constraints (one cari per book+entity)
    guarantee idempotency: calling this multiple times for the same
    customer reuses the existing row.
    """
    contact = getattr(order, "contact", None)
    company = getattr(order, "company", None) or (
        getattr(contact, "company", None) if contact else None
    )

    if company:
        return get_or_create_cari_for_company(company, member=member)

    if contact:
        return get_or_create_cari_for_contact(contact, member=member)

    return None


def get_or_create_cari_for_contact(contact, *, member=None) -> CariAccount:
    """Find (or create) the contact's cari — every B2B contact gets one
    so orders/invoices can post against it. Idempotent via the
    uniq_cari_book_contact constraint (one cari per book+contact)."""
    book = get_default_book()
    cari = CariAccount.objects.filter(book=book, contact=contact).first()
    if cari:
        return cari
    return CariAccount.objects.create(
        book=book, contact=contact,
        name=getattr(contact, "name", "") or f"Contact #{contact.pk}",
        type="customer",
        default_currency=_resolve_currency(),
        created_by=member,
    )


def get_or_create_cari_for_company(company, *, member=None) -> CariAccount:
    """Find (or create) the company's cari — every B2B company gets one
    so orders/invoices can post against it. Idempotent via the
    uniq_cari_book_company constraint (one cari per book+company)."""
    book = get_default_book()
    cari = CariAccount.objects.filter(book=book, company=company).first()
    if cari:
        return cari
    return CariAccount.objects.create(
        book=book, company=company,
        name=getattr(company, "name", "") or f"Company #{company.pk}",
        type="customer",
        default_currency=_resolve_currency(),
        created_by=member,
    )


def get_or_create_cari_for_supplier(supplier, *, member=None) -> CariAccount:
    """Find (or create) the supplier's cari — every supplier gets one so
    purchases (stock intake) can post debt against it. Idempotent via
    the uniq_cari_book_supplier constraint (one cari per book+supplier)."""
    book = get_default_book()
    cari = CariAccount.objects.filter(book=book, supplier=supplier).first()
    if cari:
        return cari
    return CariAccount.objects.create(
        book=book, supplier=supplier,
        name=str(supplier) or f"Supplier #{supplier.pk}",
        type="supplier",
        default_currency=_resolve_currency(),
        created_by=member,
    )


def _currency_by_code(code) -> CurrencyCategory:
    """Map a plain currency code string ("USD"/"TRY"/"EUR", any case) to
    a CurrencyCategory row, falling back to the base currency."""
    code = (code or "").strip()
    if code:
        cur = CurrencyCategory.objects.filter(code__iexact=code).first()
        if cur:
            return cur
    return _resolve_currency()


def create_purchase_invoice_for_intake(supplier, lines, *, member=None, user=None, invoice_date=None):
    """Turn a warehouse stock intake into an issued PURCHASE invoice
    (alış faturası) on the supplier's cari.

    `lines` = [{"description", "quantity", "unit", "unit_price",
                "currency", "product" (marketing.Product|None),
                "variant" (marketing.ProductVariant|None)}, ...]

    Creates Invoice(type="purchase", series="ALIM") + one InvoiceItem per
    line (tax 0 — the entered price is what we owe), then issue()s it,
    which posts the CariMovement(invoice_purchase, -total) with a source
    link so the cari statement row is clickable through to the invoice.
    Returns the issued Invoice.
    """
    from .models import Invoice, InvoiceItem

    book = get_default_book()
    cari = get_or_create_cari_for_supplier(supplier, member=member)
    currency = _currency_by_code(lines[0].get("currency") if lines else None)
    settings_obj = CariSettings.for_book(book)

    with transaction.atomic():
        today = invoice_date or date.today()
        term_days = cari.payment_term_days or 30
        from datetime import timedelta
        inv = Invoice.objects.create(
            cari=cari, book=book,
            series="ALIM",
            number=settings_obj.next_invoice_number(series="ALIM"),
            type="purchase", status="draft",
            date=today, due_date=today + timedelta(days=term_days),
            currency=currency,
            created_by=member,
        )
        for i, line in enumerate(lines, start=1):
            InvoiceItem.objects.create(
                invoice=inv, line_no=i,
                product=line.get("product"),
                variant=line.get("variant"),
                description=(line.get("description") or "")[:300],
                quantity=line.get("quantity") or Decimal("0"),
                unit=(line.get("unit") or "mt")[:20],
                unit_price=line.get("unit_price") or Decimal("0"),
                discount_rate=Decimal("0"),
                tax_rate=Decimal("0"),
            )
        # InvoiceItem.save computes per-line amounts; roll them up, then
        # refresh the instance so issue() posts the real total (the
        # .update() in recompute_totals doesn't touch our in-memory obj).
        inv.recompute_totals(save=True)
        inv.refresh_from_db()
        inv.issue(user=user)
    return inv


def sync_purchase_invoice_items(invoice, line_updates, *, member=None):
    """Apply an edit-diff to a purchase invoice's items IN PLACE.

    Never deletes and recreates `InvoiceItem` rows — that's exactly what the
    generic invoice editor does, and because `WarehouseProductRoll.
    purchase_invoice_item` is SET_NULL, that wipe+recreate silently orphans
    the roll↔invoice-item traceability link every time. This updates
    existing items in place and only ever CREATEs a row for a genuinely new
    line, so existing roll links on unchanged/updated lines are never
    touched.

    `line_updates` — one dict per surviving/new purchase line:
      {"invoice_item_id": <id> | None,      # None → brand-new line
       "product": marketing.Product | None,
       "variant": marketing.ProductVariant | None,
       "description": str, "unit": str, "unit_price": Decimal,
       "quantity": Decimal,                 # recomputed from roll.meters
                                             # (NOT meters_remaining) across
                                             # this line's surviving + new tops
       "new_roll_ids": [int, ...]}          # rolls to backfill onto this item

    A line whose resulting quantity is 0 (every top removed, nothing added
    back) has its InvoiceItem deleted outright — no $0 ghost lines; its
    `post_delete` signal recomputes the invoice total for free.

    Returns the invoice, refreshed with final totals.
    """
    from operating.models import WarehouseProductRoll
    from .models import InvoiceItem

    existing_items = {it.pk: it for it in invoice.items.all()}
    next_line_no = max((it.line_no for it in existing_items.values()), default=0) + 1

    for line in line_updates:
        item_id = line.get("invoice_item_id")
        qty = line.get("quantity") or Decimal("0")
        new_roll_ids = line.get("new_roll_ids") or []

        if item_id:
            item = existing_items.get(item_id)
            if item is None:
                continue  # defensive — shouldn't happen, caller owns validation
            if qty <= 0 and not new_roll_ids:
                item.delete()
                continue
            item.quantity = qty
            if line.get("unit_price") is not None:
                item.unit_price = line["unit_price"]
            if line.get("unit"):
                item.unit = line["unit"][:20]
            if line.get("description"):
                item.description = line["description"][:300]
            item.save()
            if new_roll_ids:
                WarehouseProductRoll.objects.filter(pk__in=new_roll_ids).update(
                    purchase_invoice_item=item
                )
        else:
            if qty <= 0:
                continue
            item = InvoiceItem.objects.create(
                invoice=invoice, line_no=next_line_no,
                product=line.get("product"), variant=line.get("variant"),
                description=(line.get("description") or "")[:300],
                quantity=qty, unit=(line.get("unit") or "mt")[:20],
                unit_price=line.get("unit_price") or Decimal("0"),
                discount_rate=Decimal("0"), tax_rate=Decimal("0"),
            )
            next_line_no += 1
            if new_roll_ids:
                WarehouseProductRoll.objects.filter(pk__in=new_roll_ids).update(
                    purchase_invoice_item=item
                )

    invoice.recompute_totals(save=True)
    invoice.refresh_from_db()
    return invoice


def create_invoice_for_order(order, *, user=None):
    """Auto-issue the sales invoice for a completed (shipped) order.

    Called from apply_order_status_change the moment an order enters a
    shipped status — the invoice is the paper trail of the completed
    sale. Lines mirror the order items, but their QUANTITY is the
    actually scanned/packed amount (order.get_billable_line_quantities()),
    not the ordered quantity — packing and the order detail can genuinely
    disagree (extra or short rolls scanned), and the invoice/cari must
    bill reality, not the original request. 0% tax so the invoice total
    equals order.billable_value(), i.e. exactly the receivable the
    order_sale movement already posted (issue() posts a 0-amount marker
    for order-linked invoices — no double counting). A line whose
    billable quantity is 0 (nothing scanned, e.g. it was dropped/never
    packed) is skipped entirely rather than invoiced as zero.

    Idempotent: an order that already has a non-cancelled invoice is
    left alone (re-ship after un-ship creates a fresh one only because
    un-shipping cancels the old). Returns the Invoice or None.
    """
    from .models import Invoice, InvoiceItem

    if not order or not order.cari_id:
        return None
    if order.invoices.exclude(status="cancelled").exists():
        return None
    try:
        total = Decimal(str(order.billable_value() or 0))
    except Exception:
        total = Decimal("0")
    if total <= 0:
        return None

    cari = order.cari
    book = cari.book or get_default_book()
    settings_obj = CariSettings.for_book(book)
    member = getattr(user, "member", None) if user else None
    today = date.today()
    from datetime import timedelta
    term_days = cari.payment_term_days or 30

    qty_map = order.get_billable_line_quantities()

    with transaction.atomic():
        inv = Invoice.objects.create(
            cari=cari, book=book,
            series="FAT",
            number=settings_obj.next_invoice_number(series="FAT"),
            type="sales", status="draft",
            date=today, due_date=today + timedelta(days=term_days),
            currency=cari.default_currency or _resolve_currency(order),
            order=order,
            created_by=member,
        )
        line_no = 0
        for it in order.items.all():
            qty = qty_map.get(it.pk, it.quantity or Decimal("0"))
            if not qty or qty <= 0:
                continue
            line_no += 1
            desc = ""
            if getattr(it, "product_variant_id", None) and it.product_variant:
                # Name the VARIANT, not just the base product — staff can't
                # tell "2086 [KZL000344]" apart; "2086 — GÜMÜŞ A.BEYAZ
                # [KZL000344]" they can. Same labeling as the order screens.
                label = None
                try:
                    from operating.views import _order_item_variant_label
                    label = _order_item_variant_label(it)
                except Exception:
                    label = None
                title = (it.product.title or "") if getattr(it, "product_id", None) else ""
                sku = it.product_variant.variant_sku or ""
                base = f"{title} — {label}" if (title and label) else (label or title)
                desc = f"{base} [{sku}]" if sku else base
            elif getattr(it, "product_id", None) and it.product:
                desc = it.product.title
            InvoiceItem.objects.create(
                invoice=inv, line_no=line_no,
                product=it.product,
                variant=getattr(it, "product_variant", None),
                order_item=it,
                description=(desc or "Item")[:300],
                quantity=qty,
                unit="mt",
                unit_price=it.price or Decimal("0"),
                discount_rate=Decimal("0"),
                tax_rate=Decimal("0"),
            )
        inv.recompute_totals(save=True)
        inv.refresh_from_db()
        inv.issue(user=user)
    return inv


# ---------------------------------------------------------------------------
# Movements — keep the order ↔ movement mapping atomic + idempotent.
# ---------------------------------------------------------------------------
def _order_movement(order):
    """Return the existing 'order_sale' movement for this order, if any.

    Uses CariMovement's generic source FK so we can look the row up
    without storing a pointer on Order itself.
    """
    if not order or not order.pk:
        return None
    ct = ContentType.objects.get_for_model(order.__class__)
    return CariMovement.objects.filter(
        source_type=ct, source_id=order.pk, movement_type="order_sale",
    ).first()


@transaction.atomic
def post_order_movement(order, *, member=None):
    """Create (or update) the cari movement that represents this order.

    Sign convention: order_sale is a debit on the customer (+ amount —
    the customer owes us more once the order goes out). This mirrors
    invoice_sale; the customer's cari balance reflects pending orders
    even before a formal invoice is issued.

    The amount is order.billable_value() — price × ACTUALLY SCANNED/
    PACKED quantity per line (see Order.get_billable_line_quantities) —
    not the ordered total. An order sitting there with items but nothing
    scanned yet posts 0 and carries no receivable; the receivable grows
    live as staff scan barcodes into packing, and reflects real
    shortages/overages if what got scanned differs from what was
    ordered. Called both by the OrderItem save signal (order edits) and
    by every packing/reservation endpoint (scan add/update/remove/
    assign-pack, consume/restore at ship/un-ship) so the cari tracks
    packing in real time, not just order edits.

    Idempotent: re-running after an edit updates the amount in place
    instead of creating a duplicate movement.
    """
    if not order or not order.pk:
        return None

    cari = order.cari
    if not cari:
        return None

    # Compute total from what was actually scanned/packed, not what was
    # ordered — see Order.billable_value().
    try:
        total = Decimal(str(order.billable_value() or 0))
    except Exception:
        total = Decimal("0")

    existing = _order_movement(order)

    # A cancelled order must never carry a receivable — item edits fire
    # the OrderItem sync signal regardless of status, and without this
    # guard such an edit would silently resurrect the reversed movement.
    if total <= 0 or getattr(order, "order_status", "") == "cancelled":
        if existing:
            existing.delete()
            cari.recompute_balance(save=True)
        return None

    book = get_default_book()
    currency = _resolve_currency(order)
    ref = order.order_number or f"ORD-{order.pk}"
    desc = f"Order #{order.pk}"

    if existing:
        # Update in place — keeps the movement's id stable and avoids
        # phantom rows in the ledger UI.
        existing.amount = total
        existing.currency = currency
        existing.book = book
        existing.date = order.created_at.date() if order.created_at else date.today()
        existing.description = desc
        existing.reference = ref
        # Force amount_base recompute on save.
        existing.amount_base = Decimal("0")
        existing.save()
        return existing

    return CariMovement.objects.create(
        cari=cari,
        book=book,
        date=order.created_at.date() if order.created_at else date.today(),
        amount=total,
        currency=currency,
        movement_type="order_sale",
        source_type=ContentType.objects.get_for_model(order.__class__),
        source_id=order.pk,
        description=desc,
        reference=ref,
        created_by=member,
    )


def reverse_order_movement(order):
    """Delete the cari movement tied to this order (e.g. on order
    deletion or cancellation). Cari balance is recomputed inside
    CariMovement.delete via the standard model flow."""
    mv = _order_movement(order)
    if not mv:
        return
    cari = mv.cari
    mv.delete()
    if cari:
        cari.recompute_balance(save=True)


# ---------------------------------------------------------------------------
# Perakende (retail) — anonymous walk-in sales.
#
# Retail orders have no contact/company, so get_or_create_cari_for_order
# returns None and their revenue would vanish from the books entirely.
# Instead they all post to ONE shared system cari ("Perakende
# Satışları") when the order COMPLETES (moves to shipped): the sale
# movement plus an automatic cash collection for whatever a deposit
# hasn't already covered — retail is paid at the counter, so the cari
# balance nets to ~0 and the account reads as a retail revenue journal.
# The same completion also writes an EquityRevenue row into the
# "Perakende" accounting Book so the defter mirrors the sale.
# ---------------------------------------------------------------------------
RETAIL_CARI_CODE = "PERAKENDE"
RETAIL_BOOK_NAME = "Perakende"
RETAIL_CASH_NAME = "Perakende Kasa"
_RETAIL_AUTO_DESC = "Perakende otomatik tahsilat"


def get_or_create_retail_cari(member=None) -> CariAccount:
    """The single shared cari all retail orders post to."""
    book = get_default_book()
    cari = CariAccount.objects.filter(book=book, code=RETAIL_CARI_CODE).first()
    if cari:
        return cari
    return CariAccount.objects.create(
        book=book, code=RETAIL_CARI_CODE, name="Perakende Satışları",
        type="customer", default_currency=_resolve_currency(),
        notes="Sistem carisi — anonim perakende satışlar otomatik buraya işlenir.",
        created_by=member,
    )


def _get_retail_book():
    book = Book.objects.filter(name__iexact=RETAIL_BOOK_NAME).first()
    if book:
        return book
    return Book.objects.create(name=RETAIL_BOOK_NAME)


def _get_retail_cash_account(currency):
    from accounting.models import CashAccount
    book = _get_retail_book()
    acc = CashAccount.objects.filter(book=book, name=RETAIL_CASH_NAME,
                                     currency=currency).first()
    if acc:
        return acc
    return CashAccount.objects.create(book=book, name=RETAIL_CASH_NAME,
                                      currency=currency, balance=0)


def _order_confirmed_collections(order, cari):
    """Sum of confirmed collections already tagged to this order on the
    retail cari (deposits + a possibly-existing auto collection)."""
    from .models import Payment
    from django.db.models import Sum
    return (Payment.objects.filter(
        cari=cari, type="collection", status="confirmed",
        notes=f"ORD-{order.pk}",
    ).aggregate(s=Sum("amount"))["s"] or Decimal("0"))


def post_retail_order_financials(order, user=None):
    """Idempotent completion posting for a retail order:
      1. attach the shared retail cari + post the order_sale movement;
      2. auto-collect the not-yet-collected remainder (cash, no
         cash_account — physical cash is tracked by the defter side);
      3. mirror the sale into the Perakende Book as EquityRevenue
         (+ CashTransactionEntry + till balance via the standard
         handle_equity_transaction machinery).
    Safe to re-run (re-ship after un-ship): each leg checks its own
    marker before writing."""
    from .models import Payment
    from .views_payment import _next_payment_number
    from accounting.models import EquityRevenue

    member = getattr(user, "member", None) if user else None
    total = Decimal(str(order.total_value() or 0))
    if total <= 0:
        return

    cari = get_or_create_retail_cari(member=member)
    if order.cari_id != cari.pk:
        order.cari = cari
        order.save(update_fields=["cari", "updated_at"])
    post_order_movement(order, member=member)

    # ── auto collection for the remainder ────────────────────────
    currency = _resolve_currency(order)
    collected = _order_confirmed_collections(order, cari)
    remainder = total - collected
    if remainder > 0:
        book = get_default_book()
        pay = Payment.objects.create(
            cari=cari, book=book,
            number=_next_payment_number(book, "collection"),
            type="collection", method="cash", status="draft",
            date=date.today(), amount=remainder, currency=currency,
            description=f"{_RETAIL_AUTO_DESC} — Sipariş #{order.pk}",
            notes=f"ORD-{order.pk}",
            created_by=member,
        )
        pay.confirm(user=user)

    # ── defter (Perakende Book) mirror ───────────────────────────
    retail_book = _get_retail_book()
    if not EquityRevenue.objects.filter(order=order, book=retail_book).exists():
        cash_acc = _get_retail_cash_account(currency)
        rev = EquityRevenue.objects.create(
            book=retail_book, cash_account=cash_acc, currency=currency,
            amount=total, date=date.today(),
            description=f"Perakende satış — Sipariş #{order.pk}",
            order=order, revenue_type="sales",
        )
        from accounting.views import handle_equity_transaction
        handle_equity_transaction(retail_book, total, currency, rev, rev.pk, cash_acc)


def reverse_retail_order_financials(order, user=None):
    """Undo post_retail_order_financials when a retail order leaves the
    shipped state (un-ship / cancel): remove the sale movement, cancel
    the AUTO collection (manual deposits are left alone), and reverse
    the defter revenue + till cash."""
    from .models import Payment
    from accounting.models import EquityRevenue, CashAccount, CashTransactionEntry
    from django.db.models import F as _F

    reverse_order_movement(order)

    cari = CariAccount.objects.filter(book=get_default_book(),
                                      code=RETAIL_CARI_CODE).first()
    if cari:
        for pay in Payment.objects.filter(
                cari=cari, type="collection", status="confirmed",
                notes=f"ORD-{order.pk}",
                description__startswith=_RETAIL_AUTO_DESC):
            pay.cancel(user=user, reason="Sipariş sevk iptali")

    retail_book = Book.objects.filter(name__iexact=RETAIL_BOOK_NAME).first()
    if retail_book:
        for rev in EquityRevenue.objects.filter(order=order, book=retail_book):
            # Pull the cash back out of the till + drop the ledger rows.
            # queryset.update bypasses CashAccount.clean's >=0 guard on
            # purpose: the reversal must post even if the till was
            # drained by other entries in the meantime.
            CashAccount.objects.filter(pk=rev.cash_account_id).update(
                balance=_F("balance") - rev.amount)
            ct = ContentType.objects.get_for_model(EquityRevenue)
            CashTransactionEntry.objects.filter(
                book=retail_book, content_type=ct, content_pk=rev.pk).delete()
            rev.delete()
