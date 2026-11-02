"""The Etsy sync: what the shop did since the last run, into the books.

For a connection that has been switched on, everything Etsy shows from its
`sync_from` moment is recorded once — each receipt and each ledger entry is
kept by its Etsy id (EtsyReceipt, EtsyLedgerEntry), so running again, or
twice at the same time, records nothing twice:

  * an Etsy order becomes a DRAFT order to Etsy's company, from the chosen
    warehouse, priced as sold without tax, its discount and any shipping
    charge as the order's adjustments. A person picks its boxes and
    completes it; the sale is recorded then, as for any order.
  * an Etsy fee becomes an expense in the chosen category, paid by Etsy's
    account.
  * a payout to the bank becomes a dividend to the chosen stakeholder, paid
    by Etsy's account.
  * a buyer's payment and the sales tax taken back off it are covered by
    the order, and written nowhere.

What it cannot be sure of waits for a person rather than being guessed: an
order whose SKU is not on the shelf, a refund, a cancellation, money
coming in that is not a buyer's payment, a currency that is not the
account's. Each thing is recorded in its own transaction, so one that
cannot be recorded never holds back the rest.
"""
import threading
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db import IntegrityError, connection as db_connection, transaction
from django.utils import timezone

from . import etsy_api
from .etsy_preview import FEE, PAYOUT, SALE, TAX, classify
from .models import (COVERED, NEEDS_PERSON, RECORDED, SKIPPED, EtsyConnection,
                     EtsyLedgerEntry, EtsyReceipt)

EVERY = 60 * 60                 # once an hour at most, per server process
OVERLAP = timedelta(days=3)     # read back a little, in case Etsy posts late
CENTS = Decimal("100")


def _when(seconds):
    return datetime.fromtimestamp(int(seconds), tz=timezone.utc)


def _member(connection):
    user = connection.connected_by
    return getattr(user, "member", None) if user else None


# ── Orders ────────────────────────────────────────────────────────────────
def record_receipt(connection, r):
    """Draft the order for one Etsy receipt, or say why a person must."""
    from accounting.services_accounts import post_order_movement, stamp_order_currency
    from operating.models import Order, OrderItem, WarehouseProduct
    from operating.views import save_order_adjustments

    receipt_id = int(r["receipt_id"])
    created = _when(r.get("created_timestamp") or r.get("create_timestamp"))
    status = (r.get("status") or "").lower()

    def note(state, problem="", order=None):
        EtsyReceipt.objects.create(connection=connection, receipt_id=receipt_id, created=created,
                                   state=state, problem=problem, order=order)

    if "cancel" in status:
        return note(SKIPPED, "Cancelled on Etsy.")
    if "refund" in status or r.get("refunds"):
        return note(NEEDS_PERSON, "Refunded on Etsy: decide whether the goods came back.")

    account = connection.current_account
    shelf = {w.sku: w for w in WarehouseProduct.objects.filter(warehouse=connection.warehouse)
             .select_related("catalog_variant__product")}
    lines, missing = [], []
    for t in r.get("transactions") or []:
        row = shelf.get((t.get("sku") or "").strip())
        if row is None or row.catalog_variant_id is None:
            missing.append(t.get("sku") or "(no SKU)")
            continue
        lines.append((row.catalog_variant, Decimal(t.get("quantity") or 0),
                      etsy_api.money(t.get("price"))))
    if missing or not lines:
        return note(NEEDS_PERSON, "Not on the shelf: " + ", ".join(missing or ["no lines"]))
    currency = (r.get("grandtotal") or {}).get("currency_code") or ""
    if currency and account.default_currency.code != currency:
        return note(NEEDS_PERSON, f"Sold in {currency}; Etsy's account is in "
                                  f"{account.default_currency.code}.")

    order = Order.objects.create(
        company=account.company, current_account=account,
        created_by=connection.connected_by, order_date=timezone.localtime(created).date(),
        notes=f"Etsy order #{receipt_id} · {r.get('name') or ''}".strip(" ·"),
    )
    for variant, quantity, price in lines:
        OrderItem.objects.create(order=order, product=variant.product, product_variant=variant,
                                 quantity=quantity, price=price)
    adjustments = []
    discount = etsy_api.money(r.get("discount_amt"))
    if discount:
        adjustments.append({"label": "Etsy discount", "amount": str(-discount)})
    shipping = etsy_api.money(r.get("total_shipping_cost"))
    if shipping:
        adjustments.append({"label": "Shipping", "amount": str(shipping)})
    save_order_adjustments(order, adjustments)
    stamp_order_currency(order, account)
    post_order_movement(order, member=_member(connection))  # nothing yet: an open order is no sale

    # What Etsy says the buyer bought, without tax, against what the order bills.
    expected = etsy_api.money(r.get("subtotal")) + shipping
    order.refresh_from_db()
    billed = order.billable_value()
    problem = "" if billed == expected else (
        f"The order bills {billed}; Etsy's goods less discount plus shipping come to {expected}.")
    note(RECORDED, problem, order=order)
    return order


# ── Ledger ────────────────────────────────────────────────────────────────
def record_entry(connection, e):
    """Record one ledger entry as what it is, or say why a person must."""
    from accounting.models import EquityDivident, EquityExpense
    from accounting.views import post_cash_outflow, post_expense

    account = connection.current_account
    amount = Decimal(e.get("amount") or 0) / CENTS
    kind = classify(e)
    row = EtsyLedgerEntry(
        connection=connection, entry_id=int(e["entry_id"]),
        created=_when(e.get("created_timestamp") or e.get("create_date")),
        ledger_type=str(e.get("ledger_type") or "")[:64],
        reference_type=str(e.get("reference_type") or "")[:64],
        reference_id=str(e.get("reference_id") or "")[:64],
        amount=amount, balance=Decimal(e.get("balance") or 0) / CENTS,
        currency=str(e.get("currency") or "")[:3], kind=kind, state=NEEDS_PERSON,
    )
    day = timezone.localtime(row.created).date()
    what = f"Etsy {row.ledger_type} · {row.reference_type} {row.reference_id}".strip()
    if row.currency and row.currency != account.default_currency.code:
        row.problem = f"In {row.currency}; Etsy's account is in {account.default_currency.code}."
    elif kind in (SALE, TAX):
        row.state = COVERED
    elif kind == FEE:
        expense = EquityExpense.objects.create(
            book=connection.book, category=connection.fee_category,
            paid_by_current_account=account, currency=account.default_currency,
            amount=-amount, date=day, description=what[:200])
        post_expense(connection.book, expense, _member(connection))
        row.expense, row.state = expense, RECORDED
    elif kind == PAYOUT:
        dividend = EquityDivident(
            book=connection.book, member=connection.payout_member,
            paid_by_current_account=account, currency=account.default_currency,
            amount=-amount, date=day, description=f"Etsy payout to the bank · {row.reference_id}"[:200])
        dividend.full_clean()
        post_cash_outflow(connection.book, dividend, _member(connection))
        row.dividend, row.state = dividend, RECORDED
    else:
        row.problem = ("A refund: record what came back by hand." if "refund" in what.lower()
                       else "Not a payment, fee or payout the sync knows.")
    row.save()
    return row


# ── A run ─────────────────────────────────────────────────────────────────
def sync(connection, now=None):
    """Record everything new since `sync_from`. Returns (recorded, waiting)."""
    if not connection.is_syncing:
        return 0, 0
    if connection.missing_settings():
        raise etsy_api.EtsyError("Choose " + ", ".join(connection.missing_settings())
                                 + " before the sync can record.")
    now = now or timezone.now()
    start = max(connection.sync_from, (connection.last_synced_at or connection.sync_from) - OVERLAP)
    client = etsy_api.EtsyClient(connection)
    receipts = client.receipts(connection.shop_id, start, now)
    entries = client.ledger_entries(connection.shop_id, start, now)

    seen_receipts = set(connection.receipts.values_list("receipt_id", flat=True))
    seen_entries = set(connection.ledger_entries.values_list("entry_id", flat=True))
    for r in receipts:
        created = _when(r.get("created_timestamp") or r.get("create_timestamp"))
        if int(r["receipt_id"]) in seen_receipts or created < connection.sync_from:
            continue
        try:
            with transaction.atomic():
                record_receipt(connection, r)
        except IntegrityError:
            pass        # another run recorded it a moment ago
    for e in sorted(entries, key=lambda e: (e.get("created_timestamp") or 0,
                                            e.get("sequence_number") or 0)):
        created = _when(e.get("created_timestamp") or e.get("create_date"))
        if int(e["entry_id"]) in seen_entries or created < connection.sync_from:
            continue
        try:
            with transaction.atomic():
                record_entry(connection, e)
        except IntegrityError:
            pass
    this_run = [qs.filter(synced_at__gte=now) for qs in (connection.receipts, connection.ledger_entries)]
    recorded = sum(qs.exclude(state=NEEDS_PERSON).count() for qs in this_run)
    waiting = sum(qs.filter(state=NEEDS_PERSON).count() for qs in this_run)
    connection.last_synced_at = now
    connection.last_sync_error = ""
    connection.save(update_fields=["last_synced_at", "last_sync_error", "updated_at"])
    return recorded, waiting


def sync_all():
    """One run for every connection that is switched on. Never raises."""
    for connection in EtsyConnection.objects.filter(sync_from__isnull=False).select_related(
            "book", "current_account__default_currency", "current_account__company",
            "warehouse", "fee_category", "payout_member", "connected_by"):
        try:
            sync(connection)
        except Exception as exc:          # the reason is shown on the Etsy page
            EtsyConnection.objects.filter(pk=connection.pk).update(
                last_sync_error=str(exc)[:1000])


def sync_now_and_then():
    """At most once an hour, off the request: the ERP's own use is the clock,
    as for product_images.housekeep_now_and_then. A process that has run in
    the last hour does nothing; a second process that runs anyway finds
    every Etsy id already kept and records nothing twice."""
    if not etsy_api.app_configured() or not cache.add("etsy-sync", True, EVERY):
        return

    def work():
        try:
            sync_all()
        finally:
            db_connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())
