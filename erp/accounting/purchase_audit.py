"""Purchase audit trail — every meaningful change to a purchase as a
PurchaseChange row, the purchase-side twin of operating/audit.py.

An order's audit is signal-driven because an order is rows: an OrderItem
saved is a change seen. A purchase is one JSON plan (Invoice.intake_plan)
rewritten whole on every save, so the only way to say what changed is to
compare the plan as it was with the plan as it is — which is what
diff_plans does, called by the save view and by the order→purchase
mirror with the plan before and after.

Every helper is exception-safe: auditing must never break a save.
"""
from decimal import Decimal, InvalidOperation

from .models_accounts import PurchaseChange

# The scalar fields a purchase carries besides its lines, and what each
# is called in the log.
FIELD_LABELS = {
    "date": "date",
    "delivery_date": "delivery date",
    "supplier": "supplier",
    "warehouse": "warehouse",
    "notes": "notes",
    "status": "status",
    "order": "customer order",
}


def _user(user):
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    from operating.audit import get_current_user
    return get_current_user()


def log_purchase(invoice, action, *, field=None, item_label=None, old=None, new=None,
                 origin="purchase", user=None):
    """`invoice` may be an Invoice or a raw id."""
    try:
        PurchaseChange.objects.create(
            invoice_id=getattr(invoice, "pk", invoice),
            action=action,
            field=field,
            item_label=(item_label or "")[:255] or None,
            old_value=(str(old) if old not in (None, "") else None),
            new_value=(str(new) if new not in (None, "") else None),
            origin=origin,
            created_by=_user(user),
        )
    except Exception:
        pass


def _dec(value):
    try:
        return Decimal(str(value if value not in (None, "") else "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _num(d):
    """A Decimal without trailing zeros, for a log line: 55.000 → 55."""
    d = _dec(d)
    return str(d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize())


def plan_rows(plan):
    """{sku: {label, quantity, price, currency, sale_price}} for every row
    of a plan that names a SKU — rows are matched between two plans by it."""
    from operating.order_purchases import _row_quantity
    from operating.views_warehouse import _row_label

    rows = {}
    for p_in in (plan or {}).get("products") or []:
        mp = p_in.get("main_product") or {}
        product = (mp.get("title") or mp.get("name") or mp.get("sku") or "").strip()
        for v_in in p_in.get("variants") or []:
            sku = (v_in.get("sku") or "").strip()
            if not sku:
                continue
            label = " ".join(x for x in (product, _row_label(v_in)) if x)
            rows[sku.lower()] = {
                "label": f"{label} [{sku}]" if label else sku,
                "quantity": _row_quantity(v_in),
                "price": _dec(v_in.get("price")),
                "currency": (v_in.get("currency") or "").strip(),
                "sale_price": _dec(v_in.get("sale_price")),
            }
    return rows


def _money(amount, currency):
    return f"{_num(amount)} {currency}".strip()


def _summary(row):
    s = f"{_num(row['quantity'])} × {_money(row['price'], row['currency'])}"
    if row["sale_price"] > 0:
        s += f" · sells at {_num(row['sale_price'])}"
    return s


def diff_plans(invoice, old_plan, new_plan, *, origin="purchase", user=None):
    """Log what changed between two plans of the same purchase: rows added
    and removed, and a row's quantity, purchase price or sale price."""
    try:
        old, new = plan_rows(old_plan), plan_rows(new_plan)
    except Exception:
        return
    for sku, row in new.items():
        was = old.get(sku)
        if was is None:
            log_purchase(invoice, "item_added", item_label=row["label"],
                         new=_summary(row), origin=origin, user=user)
            continue
        if was["quantity"] != row["quantity"]:
            log_purchase(invoice, "item_updated", field="quantity", item_label=row["label"],
                         old=_num(was["quantity"]), new=_num(row["quantity"]),
                         origin=origin, user=user)
        if was["price"] != row["price"] or was["currency"] != row["currency"]:
            log_purchase(invoice, "item_updated", field="price", item_label=row["label"],
                         old=_money(was["price"], was["currency"]),
                         new=_money(row["price"], row["currency"]),
                         origin=origin, user=user)
        if was["sale_price"] != row["sale_price"]:
            log_purchase(invoice, "item_updated", field="sale_price", item_label=row["label"],
                         old=_num(was["sale_price"]), new=_num(row["sale_price"]),
                         origin=origin, user=user)
    for sku, was in old.items():
        if sku not in new:
            log_purchase(invoice, "item_removed", item_label=was["label"],
                         old=_summary(was), origin=origin, user=user)


def snapshot_fields(invoice):
    """The purchase's scalar fields as the log compares them."""
    if invoice is None or not invoice.pk:
        return {}
    try:
        return {
            "date": invoice.date.isoformat() if invoice.date else "",
            "delivery_date": invoice.delivery_date.isoformat() if invoice.delivery_date else "",
            "supplier": invoice.current_account.name if invoice.current_account_id else "",
            "warehouse": invoice.intake_warehouse.name if invoice.intake_warehouse_id else "",
            "notes": invoice.notes or "",
        }
    except Exception:
        return {}


def diff_fields(invoice, before, *, origin="purchase", user=None):
    """Log each scalar field of `invoice` that differs from `before`
    (a snapshot_fields() result)."""
    if not before:
        return
    now = snapshot_fields(invoice)
    for field, old in before.items():
        new = now.get(field, "")
        if (old or "") != (new or ""):
            log_purchase(invoice, "field", field=field, old=old, new=new,
                         origin=origin, user=user)


def decorate_changes(changes):
    """Attach the display strings the purchase page prints."""
    from django.utils.translation import gettext as _
    labels = {
        "date": _("date"), "delivery_date": _("delivery date"),
        "supplier": _("supplier"), "warehouse": _("warehouse"),
        "notes": _("notes"), "status": _("status"), "order": _("customer order"),
        "quantity": _("quantity"), "price": _("price"), "sale_price": _("sale price"),
    }
    for c in changes:
        c.action_display = c.get_action_display()
        c.field_display = labels.get(c.field, (c.field or "").replace("_", " ")) if c.field else None
        c.origin_display = c.get_origin_display() if c.origin == "order" else ""
    return changes
