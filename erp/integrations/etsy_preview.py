"""What the Etsy sync would record for a stretch of time — read only.

Nothing here writes. It reads the shop's receipts and payment account
ledger for the dates asked, says what each would become in the books, and
sets that beside what Etsy's account in the ERP already holds for the same
days. Etsy does not publish the list of ledger entry types, so the meaning
of each is proposed from what the entry says, and the entries are also
grouped by Etsy's own labels: the preview is where those meanings are
checked against a month already recorded by hand, before the sync relies
on them.
"""
from collections import OrderedDict
from datetime import datetime, time
from decimal import Decimal

from django.utils import timezone

from .etsy_api import EtsyClient, money

CENTS = Decimal("100")

# What a ledger entry is for the books.
SALE = "sale"          # the buyer's payment for a receipt — the order records it
TAX = "tax"            # sales tax / VAT Etsy collects and pays on — never ours
FEE = "fee"            # Etsy's charge — an expense paid by Etsy's account
PAYOUT = "payout"      # money sent to the owner's bank — a dividend
OTHER = "other"        # anything else — for a person to decide

KIND_LABELS = {
    SALE: "Sale (recorded by the order)",
    TAX: "Sales tax (not ours)",
    FEE: "Fee (expense)",
    PAYOUT: "Payout (dividend)",
    OTHER: "Needs a person",
}


def classify(entry):
    """The meaning of one ledger entry, from what it says of itself.

    Read off the labels Etsy put on October 2026's entries, checked there
    against the month recorded by hand: PAYMENT_GROSS / shop_payment is a
    buyer's payment, sales_tax the tax taken back off it, DISBURSE2 a
    payout, and the fee labels (transaction, PAYMENT_PROCESSING_FEE,
    offsite_ads_fee, the listing renewals) all charges. Anything about a
    refund, and anything that comes in rather than goes out without being
    a buyer's payment (billing_payment: the owner's card settling Etsy's
    bill), is left to a person.
    """
    amount = entry.get("amount") or 0
    ledger_type = str(entry.get("ledger_type") or "")
    reference_type = str(entry.get("reference_type") or "")
    text = " ".join((ledger_type, str(entry.get("description") or ""), reference_type)).lower()
    if "refund" in text or "reversal" in text:
        return OTHER
    if "disburse" in text:
        return PAYOUT if amount < 0 else OTHER
    # VAT Etsy charges on its own services is part of the fee, not a tax we owe.
    if "tax" in text and "seller_services" not in text and "vat_seller" not in text:
        return TAX if amount < 0 else OTHER
    if amount > 0:
        is_payment = ledger_type.upper() == "PAYMENT_GROSS" or reference_type == "shop_payment"
        return SALE if is_payment else OTHER
    if amount < 0:
        return FEE
    return OTHER


def _day_range(start, end):
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(start, time.min), tz),
            timezone.make_aware(datetime.combine(end, time.max), tz))


def _when(seconds):
    return timezone.localtime(datetime.fromtimestamp(int(seconds), tz=timezone.utc)) if seconds else None


def receipt_rows(connection, receipts):
    """Each receipt as the order the sync would draft."""
    from operating.models import Order, WarehouseProduct

    on_shelf = {}
    if connection.warehouse_id:
        on_shelf = dict(WarehouseProduct.objects.filter(warehouse=connection.warehouse)
                        .values_list("sku", "catalog_variant_id"))
    rows = []
    for r in receipts:
        receipt_id = str(r.get("receipt_id"))
        lines = []
        for t in r.get("transactions") or []:
            sku = (t.get("sku") or "").strip()
            lines.append({
                "sku": sku or "—",
                "title": (t.get("title") or "")[:80],
                "quantity": t.get("quantity") or 0,
                "price": money(t.get("price")),
                "matched": bool(sku) and on_shelf.get(sku) is not None,
            })
        shipments = r.get("shipments") or []
        rows.append({
            "receipt_id": receipt_id,
            "created": _when(r.get("created_timestamp") or r.get("create_timestamp")),
            "buyer": r.get("name") or "",
            "status": r.get("status") or "",
            "shipped": bool(r.get("is_shipped")),
            "items": money(r.get("total_price")),
            "discount": money(r.get("discount_amt")),
            "shipping": money(r.get("total_shipping_cost")),
            # What the order bills Etsy: goods less discount, plus shipping;
            # never the tax, which Etsy collects and pays on.
            "sale": money(r.get("subtotal")) + money(r.get("total_shipping_cost")),
            "tax": money(r.get("total_tax_cost")) + money(r.get("total_vat_cost")),
            "tracking": ", ".join(s.get("tracking_code") or "" for s in shipments if s.get("tracking_code")),
            "lines": lines,
            "unmatched": [l["sku"] for l in lines if not l["matched"]],
            "refunded": "refund" in (r.get("status") or "").lower() or bool(r.get("refunds")),
            "recorded": Order.objects.filter(notes__icontains=f"#{receipt_id}").exists(),
        })
    return rows


def ledger_rows(entries):
    rows = []
    for e in sorted(entries, key=lambda e: (e.get("created_timestamp") or 0, e.get("sequence_number") or 0)):
        kind = classify(e)
        rows.append({
            "entry_id": e.get("entry_id"),
            "created": _when(e.get("created_timestamp") or e.get("create_date")),
            "ledger_type": e.get("ledger_type") or "",
            "reference_type": e.get("reference_type") or "",
            "reference_id": e.get("reference_id") or "",
            "description": e.get("description") or "",
            "amount": Decimal(e.get("amount") or 0) / CENTS,
            "balance": Decimal(e.get("balance") or 0) / CENTS,
            "currency": e.get("currency") or "",
            "kind": kind,
            "kind_label": KIND_LABELS[kind],
        })
    return rows


def by_label(rows):
    """Ledger entries grouped by Etsy's own labels, with the proposed meaning."""
    groups = OrderedDict()
    for row in rows:
        key = (row["ledger_type"], row["reference_type"], row["description"], row["kind"])
        g = groups.setdefault(key, {"ledger_type": key[0], "reference_type": key[1],
                                    "description": key[2], "kind_label": row["kind_label"],
                                    "count": 0, "total": Decimal("0")})
        g["count"] += 1
        g["total"] += row["amount"]
    return list(groups.values())


def erp_side(connection, start, end):
    """What Etsy's account in the ERP holds for the same days, by kind."""
    from accounting.models_accounts import CurrentAccountMovement

    totals = {"sales": Decimal("0"), "expenses": Decimal("0"), "dividends": Decimal("0"),
              "other": Decimal("0")}
    if not connection.current_account_id:
        return None
    for mv in CurrentAccountMovement.objects.filter(
            current_account=connection.current_account, date__gte=start, date__lte=end).live():
        model = mv.source_type.model if mv.source_type_id else ""
        if mv.movement_type in ("order_sale", "return_sale"):
            totals["sales"] += mv.amount
        elif model == "equityexpense":
            totals["expenses"] += mv.amount
        elif model == "equitydivident":
            totals["dividends"] += mv.amount
        else:
            totals["other"] += mv.amount
    totals["net"] = sum(totals.values())
    return totals


def preview(connection, start, end):
    """Everything the preview page shows for `start`–`end` (dates, inclusive)."""
    first, last = _day_range(start, end)
    client = EtsyClient(connection)
    receipts = receipt_rows(connection, client.receipts(connection.shop_id, first, last))
    ledger = ledger_rows(client.ledger_entries(connection.shop_id, first, last))

    def total(kind):
        return sum((r["amount"] for r in ledger if r["kind"] == kind), Decimal("0"))

    etsy = {
        "sales": sum((r["sale"] for r in receipts), Decimal("0")),
        "fees": total(FEE),
        "payouts": total(PAYOUT),
        "other": total(OTHER),
        "ledger_sales": total(SALE),
        "ledger_tax": total(TAX),
        "closing_balance": ledger[-1]["balance"] if ledger else None,
    }
    # What the books would say Etsy owes after these days: sales billed,
    # less its fees and what it paid out. Compared with Etsy's own balance.
    etsy["books_net"] = etsy["sales"] + etsy["fees"] + etsy["payouts"]
    return {
        "receipts": receipts,
        "ledger": ledger,
        "groups": by_label(ledger),
        "etsy": etsy,
        "erp": erp_side(connection, start, end),
    }
