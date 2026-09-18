"""The invoice as a printout, and nothing else.

An invoice here is a mirror: a sales order or a purchase, laid out as an
invoice for printing and for Excel. It is built on the fly from the
record it mirrors every time it is asked for, so it can never disagree
with that record — there is no invoice row to issue, sync or cancel.

The money never lives here. A sale's receivable is the order's own
current-account movement; a purchase's debt is posted by the purchase.

build_order_doc(order)       → the sales invoice of an order
build_purchase_doc(purchase) → the purchase invoice of a PO / receipt
Both return an InvoiceDoc, which invoice_document.html and
invoice_excel.build_invoice_workbook render.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from erp.branding import brand


@dataclass
class Party:
    name: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""
    tax_office: str = ""
    tax_number: str = ""
    account_id: int | None = None


@dataclass
class Line:
    sku: str
    group: str
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    rolls: list = field(default_factory=list)   # [{"barcode", "quantity"}]


@dataclass
class InvoiceDoc:
    kind: str                  # "sales" | "purchase"
    number: str                # the order / PO number — invoices have none of their own
    date: date | None
    currency_code: str
    currency_symbol: str
    issuer: Party
    party: Party               # the customer (sales) or the supplier (purchase)
    lines: list
    notes: str = ""
    book: object = None

    @property
    def total(self):
        return sum((l.total for l in self.lines), Decimal("0.00"))

    @property
    def filename(self):
        return f"invoice-{self.number}".replace("/", "-")


def _s(name):
    return brand(name)


def _issuer(book):
    """Who the document is from: the book's brand name, else the brand
    profile in settings — the same precedence the old invoice used."""
    name = ((getattr(book, "brand_name", "") or "").strip() if book else "")
    if not name:
        base = brand("BRAND_NAME") or "Nejum ERP"
        suffix = _s("BRAND_LEGAL_SUFFIX").strip()
        name = f"{base} {suffix}".strip() if suffix else base
    return Party(
        name=name,
        address=_s("BRAND_ADDRESS"), phone=_s("BRAND_PHONE"), fax=_s("BRAND_FAX"),
        email=_s("BRAND_EMAIL"), tax_office=_s("BRAND_TAX_OFFICE"),
        tax_number=_s("BRAND_TAX_NUMBER"),
    )


def _account_party(acc):
    return Party(
        name=acc.name or "",
        address=acc.billing_address or "",
        city=acc.billing_city or "",
        country=acc.billing_country or "",
        phone=acc.phone or "",
        email=acc.email or "",
        tax_office=acc.tax_office or "",
        tax_number=acc.tax_number or "",
        account_id=acc.pk,
    )


def _order_party(order):
    """An order without an account (a guest or web sale) still names its
    buyer: the delivery details it was placed with."""
    first = (getattr(order, "guest_first_name", "") or "").strip()
    last = (getattr(order, "guest_last_name", "") or "").strip()
    name = f"{first} {last}".strip() or str(order.get_client())
    return Party(
        name=name,
        address=order.billing_address or order.delivery_address or "",
        city=order.delivery_city or "",
        country=order.delivery_country or "",
        phone=order.delivery_phone or getattr(order, "guest_phone", "") or "",
        email=getattr(order, "guest_email", "") or "",
    )


def _money(v):
    return (v or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_order_doc(order):
    from .services_accounts import _invoice_line_desc, _resolve_currency

    acc = order.current_account
    book = acc.book if acc else None
    currency = (acc.default_currency if acc else None) or _resolve_currency(order)

    # Billed quantities, not raw ones — the same numbers the account and
    # the order screen state (Order.get_billable_line_quantities).
    qty_map = order.get_billable_line_quantities()
    items = (order.items
             .select_related("product", "product__category", "product_variant")
             .prefetch_related("stock_reservations__stock_item")
             .order_by("pk"))
    lines = []
    for it in items:
        qty = qty_map.get(it.pk, it.quantity or Decimal("0"))
        if not qty or qty <= 0:
            continue
        price = it.price or Decimal("0")
        variant = it.product_variant
        product = it.product
        lines.append(Line(
            sku=(variant.variant_sku if variant else "") or (product.sku if product else "") or "",
            group=(product.category.name if product and product.category_id else ""),
            description=_invoice_line_desc(it),
            quantity=qty,
            unit="mt",
            unit_price=price,
            total=_money(price * qty),
            rolls=[{"barcode": r.stock_item.barcode, "quantity": r.quantity}
                   for r in it.stock_reservations.all() if r.consumed and r.stock_item_id],
        ))

    return InvoiceDoc(
        kind="sales",
        number=order.order_number or str(order.pk),
        date=order.order_date or (order.created_at.date() if order.created_at else None),
        currency_code=getattr(currency, "code", "") or "",
        currency_symbol=getattr(currency, "symbol", "") or "",
        issuer=_issuer(book),
        party=_account_party(acc) if acc else _order_party(order),
        lines=lines,
        notes=order.notes or "",
        book=book,
    )


def build_purchase_doc(purchase):
    """`purchase` is the purchase record (stored as Invoice type=purchase)."""
    items = (purchase.items
             .select_related("product", "product__category", "variant")
             .prefetch_related("warehouse_stock_items")
             .order_by("line_no"))
    lines = [
        Line(
            sku=(it.variant.variant_sku if it.variant_id else "")
                or (it.product.sku if it.product_id else "") or "",
            group=(it.product.category.name
                   if it.product_id and it.product.category_id else ""),
            description=it.description or "",
            quantity=it.quantity or Decimal("0"),
            unit=it.unit or "",
            unit_price=it.unit_price or Decimal("0"),
            total=_money(it.total),
            rolls=[{"barcode": r.barcode, "quantity": r.quantity}
                   for r in it.warehouse_stock_items.all()],
        )
        for it in items
    ]
    return InvoiceDoc(
        kind="purchase",
        number=purchase.display_number,
        date=purchase.date,
        currency_code=purchase.currency.code if purchase.currency_id else "",
        currency_symbol=purchase.currency.symbol if purchase.currency_id else "",
        issuer=_issuer(purchase.book),
        party=_account_party(purchase.current_account),
        lines=lines,
        notes=purchase.notes or "",
        book=purchase.book,
    )
