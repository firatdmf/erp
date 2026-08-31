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

from django.conf import settings

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count

from accounting.models import Book, CurrencyCategory

from .models import CariAccount, CariMovement, CariSettings


# ---------------------------------------------------------------------------
# Book — which business a record belongs to.
# ---------------------------------------------------------------------------
def acting_member():
    """The Member whose request we are inside, or None.

    Read from the thread-local CurrentUserMiddleware already keeps for
    the audit trail, because get_default_book is called from ~15 places
    that have no member in scope (signals, model saves, form querysets)
    and threading one through all of them would be a lot of churn for a
    value the request already knows.

    Returns None outside a request — a management command, a cron job, a
    test — which is correct: work nobody is doing has no member's book.
    """
    from operating.audit import get_current_user
    user = get_current_user()
    if user is None:
        return None
    return getattr(user, "member", None)


def get_default_book(member=None) -> Book:
    """Return the Book a new customer account or invoice lands in when
    the caller has not said which.

    Not "the" ledger — every Book is its own ledger for its own
    business, and there will be several. This answers a narrower
    question the code is currently forced to answer: an Order carries no
    book, so ensure_cari_for_order has to pick one.

    The best answer to "which business is this?" is WHO IS ENTERING IT.
    One install runs several businesses at once; which one a record
    belongs to is a fact about the person at the keyboard, not about the
    server. So the acting member's own book wins, and the app-level flag
    is only what covers a member who has not picked one.

    This used to take the lowest-id Book, on the assumption that the project
    has one book company-wide. It does not. Books also carry the general
    ledger — cash accounts, expenses, receivables — so several exist for
    reasons that have nothing to do with cari, and the lowest-id one
    ("Muhammed Firat Ozturk", id 1) is not the one the ledger uses.

    The cost of getting it wrong is silent. Every auto-created account landed
    in a book nobody looked at, so a customer with a real account in the right
    book got a second, empty one, and their order posted against that. Sale
    #273 billed a shadow account holding 531.08 while the real account showed
    3,116.62. Nothing errored; the money simply went somewhere no one was
    reading.

    The answer to that was settings.CARI_BOOK_NAME — a brand constant naming
    the book, matched here at read time. That turned out to be the same bug
    wearing a different hat. A book's name is a mutable label people edit from
    the UI; the constant lives in a deploy and cannot follow. Rename the book
    and the match quietly stops matching, dropping resolution back to a guess.
    That is exactly what happened: neither book was called "DEMFIRAT" any more,
    so the name step had been dead for a while and only the account-count
    tiebreak was holding accounts in the right place. That constant is gone —
    a book is referenced by id or by a flag on the row, never by its name.

    Resolution order:

      1. Member.default_book — the member passed in, else whoever is making
         the request — provided they are still assigned that book. The most
         specific signal there is: this person works for that business.
      2. Their first assigned book, for a member who has never picked one.
         With a single assignment there is nothing to pick, which is the
         common case.
      3. settings.CARI_BOOK_ID — pins the answer from a deploy, for work
         with no member at all: cron, imports, the shell.
      4. Lowest id, then create — only reachable on a fresh install, or on
         a deployment that has left CARI_BOOK_ID unset while running
         memberless work.

    Every step falls through rather than raising: a stale id must not stop
    an order being placed.

    There used to be a Book.is_default_cari_target flag between steps 2 and
    3, plus a step that guessed the book holding the most cari accounts and
    wrote its guess back to that flag. Both are gone. An app-wide "default
    book" is a second answer to a question the working book already answers,
    and the two disagree the moment somebody's work moves; the guess was
    worse still, because it silently changed which business a record landed
    in as soon as the account counts crossed over. Which business a record
    belongs to is a fact about the person entering it. When there is no such
    person, CARI_BOOK_ID is the place to say so.
    """
    if member is None:
        member = acting_member()
    if member is not None:
        allowed = member_books(member)
        book = getattr(member, "default_book", None)
        if book is not None and allowed.filter(pk=book.pk).exists():
            return book
        book = allowed.first()
        if book is not None:
            return book

    pinned = getattr(settings, "CARI_BOOK_ID", "") or ""
    if str(pinned).strip().isdigit():
        book = Book.objects.filter(pk=int(pinned)).first()
        if book:
            return book

    return Book.objects.order_by("id").first() or Book.objects.create(name="Main Book")


def member_books(member):
    """The books this member may work in, as a queryset.

    A superuser is assigned every book implicitly — an install's owner
    should not be able to lock themselves out of a ledger by forgetting a
    row — and everybody else gets exactly what has been assigned to them.

    Returns an empty queryset for no member, which is the honest answer:
    work nobody is doing belongs to nobody's book. Callers that need one
    anyway (cron, imports) go through get_default_book and land on
    CARI_BOOK_ID.
    """
    if member is None:
        return Book.objects.none()
    user = getattr(member, "user", None)
    if user is not None and user.is_superuser:
        return Book.objects.all().order_by("name")
    return member.books.all().order_by("name")


def member_can_use_book(member, book) -> bool:
    """Whether this member may see and act on this book."""
    if book is None:
        return False
    return member_books(member).filter(pk=book.pk).exists()


def brand_name_for(book=None) -> str:
    """The name a customer-facing document signs with.

    One resolver for invoices, order emails and packing lists so the
    three never disagree about who sent them. Pass the book the document
    belongs to (an Invoice has one); order-side documents have no book
    of their own, so they get the ledger's — the same book their money
    posts to.

    Falls back to settings.BRAND_DISPLAY_NAME, then BRAND_NAME. It never
    raises: a document must still print on a database with no books.
    """
    if book is None:
        try:
            book = get_default_book()
        except Exception:
            book = None
    if book is not None:
        return book.effective_brand_name
    return (getattr(settings, "BRAND_DISPLAY_NAME", "")
            or getattr(settings, "BRAND_NAME", "")
            or "Nejum")


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


def get_or_create_cari_for_contact(contact, *, member=None, book=None) -> CariAccount:
    """Find (or create) the contact's cari — every B2B contact gets one
    so orders/invoices can post against it. Idempotent via the
    uniq_cari_book_contact constraint (one cari per book+contact).

    Pass `book` when the caller already knows which one — a book-scoped
    page does, and must not silently create the account somewhere else
    because that happens to be the member's working book."""
    book = book or get_default_book(member)
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


def get_or_create_cari_for_company(company, *, member=None, book=None) -> CariAccount:
    """Find (or create) the company's cari — every B2B company gets one
    so orders/invoices can post against it. Idempotent via the
    uniq_cari_book_company constraint (one cari per book+company).

    Pass `book` when the caller already knows which one."""
    book = book or get_default_book(member)
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


def get_or_create_cari_for_supplier(supplier, *, member=None, book=None) -> CariAccount:
    """Find (or create) the supplier's cari — every supplier gets one so
    purchases (stock intake) can post debt against it. Idempotent via
    the uniq_cari_book_supplier constraint (one cari per book+supplier).

    Pass `book` when the caller already knows which one."""
    book = book or get_default_book(member)
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


def create_purchase_invoice_for_intake(cari, lines, *, member=None, user=None,
                                       invoice_date=None, invoice=None):
    """Turn a warehouse stock intake into an issued PURCHASE invoice
    (alış faturası) on the given cari account.

    Takes the cari DIRECTLY rather than a crm.Supplier: the intake panel
    now picks the account staff actually keep the balance on, and most of
    those (imported from KARVEN) have no Supplier row to resolve through.

    `lines` = [{"description", "quantity", "unit", "unit_price",
                "currency", "product" (marketing.Product|None),
                "variant" (marketing.ProductVariant|None)}, ...]

    Creates Invoice(type="purchase", series="PUR") + one InvoiceItem per
    line (tax 0 — the entered price is what we owe), then issue()s it,
    which posts the CariMovement(invoice_purchase, -total) with a source
    link so the cari statement row is clickable through to the invoice.
    `invoice` — an existing DRAFT purchase order being confirmed. Its number,
    dates and account are already settled, so only its lines are rebuilt (from
    what actually arrived) before it is issued. Safe to wipe its items first:
    a draft has no rolls pointing at them yet, which is exactly what makes the
    order editable right up to the moment it is confirmed.

    Returns the issued Invoice.
    """
    from .models import Invoice, InvoiceItem

    # The invoice belongs in the book the account itself lives in — reading
    # the default book here would post the alım into a different ledger
    # than the balance it's supposed to move.
    book = cari.book
    # The account's own currency, not lines[0]'s. Every line reaching here
    # has already been restated into it by convert_lines_to_currency.
    currency = _currency_by_code(invoice_currency_for(cari))
    settings_obj = CariSettings.for_book(book)
    mark_as_supplier(cari)

    if invoice is not None:
        with transaction.atomic():
            invoice.items.all().delete()
            for i, line in enumerate(lines, start=1):
                InvoiceItem.objects.create(
                    invoice=invoice, line_no=i,
                    product=line.get("product"),
                    variant=line.get("variant"),
                    description=(line.get("description") or "")[:300],
                    quantity=line.get("quantity") or Decimal("0"),
                    unit=(line.get("unit") or "mt")[:20],
                    unit_price=line.get("unit_price") or Decimal("0"),
                    discount_rate=Decimal("0"),
                    tax_rate=Decimal("0"),
                )
            if invoice.currency_id != currency.pk:
                invoice.currency = currency
                invoice.save(update_fields=["currency", "updated_at"])
            invoice.recompute_totals(save=True)
            invoice.refresh_from_db()
            invoice.issue(user=user)
        return invoice

    with transaction.atomic():
        today = invoice_date or date.today()
        term_days = cari.payment_term_days or 30
        from datetime import timedelta
        inv = Invoice.objects.create(
            cari=cari, book=book,
            series="PUR",
            number=settings_obj.next_invoice_number(series="PUR"),
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


def _invoice_line_desc(order_item):
    """How an order line is named on the invoice.

    Names the VARIANT, not just the base product — staff can't tell
    "2086 [KZL000344]" apart; "2086 — GÜMÜŞ A.BEYAZ [KZL000344]" they
    can. Same labeling as the order screens. Shared by the initial cut
    and by sync_invoice_for_order so a re-synced line never renames
    itself.
    """
    it = order_item
    desc = ""
    if getattr(it, "product_variant_id", None) and it.product_variant:
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
    return (desc or "Item")[:300]


class MixedCurrencyError(Exception):
    """A line needs converting and there is no rate to do it with."""


def invoice_currency_for(cari):
    """What an alım to this account is denominated in: what we owe THEM.

    Their own default currency, falling back to the book's base when an
    account has never been given one.
    """
    from django.conf import settings as _s
    code = getattr(getattr(cari, "default_currency", None), "code", "") or ""
    return (code or getattr(_s, "BASE_CURRENCY_CODE", "USD")).upper()


def convert_lines_to_currency(lines, target_code, rates=None, *, on_date=None):
    """Restate every line in `target_code`, at the rate the receipt supplied.

    An invoice carries ONE currency. Lines used to be handed over in
    whatever each was priced in, and create_purchase_invoice_for_intake
    took the FIRST line's currency and summed the rest into it untouched —
    so a delivery priced part in dollars and part in lira was billed as
    though ₺100 were $100. Silently, with no conversion and no warning.

    `rates` maps a line currency to its rate INTO target_code, as typed on
    the receipt. Anything not given falls back to the published rate for
    the date. A line that needs converting and has NEITHER raises, because
    the one thing that must not happen here is a number being carried
    across a currency boundary as if it were already in the right one.

    The original price and its rate are appended to the line's description:
    it is the only place the converted figure can be checked back against
    what was actually agreed.
    """
    from decimal import Decimal as _D
    target = (target_code or "").upper()
    rates = {(k or "").upper(): v for k, v in (rates or {}).items()}
    out = []
    for line in lines:
        code = (line.get("currency") or target).upper()
        price = line.get("unit_price") or _D("0")
        if code == target or not price:
            out.append({**line, "currency": target})
            continue
        rate = rates.get(code)
        if rate in (None, ""):
            from accounting.services import get_exchange_rate
            rate = get_exchange_rate(code, target, on_date=on_date)
        try:
            rate = _D(str(rate)) if rate not in (None, "") else None
        except Exception:
            rate = None
        if not rate or rate <= 0:
            raise MixedCurrencyError(
                f"{code} → {target}: no rate for this receipt's date. "
                f"Enter one on the form, or price the line in {target}."
            )
        # NOT to cents. This is a UNIT price and the line multiplies it by
        # metres, so a cent rounded off here comes back multiplied — TRY
        # 100.00/m at 0.02077833 held as $2.08 billed $913.95 for a line
        # whose true cost was $913.00. InvoiceItem.unit_price carries six
        # decimals for exactly this, and InvoiceItem.compute() rounds the
        # LINE to cents, which is where rounding belongs.
        converted = (price * rate).quantize(_D("0.000001"))
        note = f" ({price} {code} @ {rate.normalize()})"
        out.append({
            **line,
            "unit_price": converted,
            "currency": target,
            "description": ((line.get("description") or "") + note)[:300],
        })
    return out


def mark_as_supplier(cari):
    """An account we have bought from is a supplier, and its type should say so.

    Buying does not stop someone being a customer — a mill that weaves for
    us and buys our seconds is both, which is why "both" is already a type
    and already has a badge on the account page. So a customer is PROMOTED
    rather than reclassified; only an account that is neither yet becomes a
    plain supplier.

    Staff is left alone deliberately. A staff account settles expenses on
    the book's behalf, and turning a colleague into a vendor because one
    receipt was posted through them is a classification nobody asked for.

    Returns True when the type actually moved.
    """
    if cari is None or not cari.pk:
        return False
    current = (cari.type or "").strip()
    if current in ("supplier", "both", "staff"):
        return False
    new_type = "both" if current == "customer" else "supplier"
    cari.type = new_type
    cari.save(update_fields=["type"])
    return True


def refresh_invoice_lines_for_variant(variant):
    """Re-render every invoice line that names `variant`, after its SKU changed.

    A line's `description` is a snapshot cut at invoicing time and it embeds
    the variant SKU ("24861T YARIMAT ALTIN — g77 [K24861T.G77]"). Renaming a
    variant used to leave every existing document still printing the dead
    code, so the invoice disagreed with the catalog and a search for the new
    SKU found none of the paperwork that quotes it.

    Same two exclusions as sync_invoice_for_order, for the same reasons:
      * draft — issue() builds its lines from the order later anyway.
      * e-Arşiv filed (earsiv_uuid) — that document went to the tax
        authority and cannot be quietly rewritten. It needs a credit note,
        which is a human decision, so it is reported back to the caller
        rather than silently diverging.
    A cancelled invoice IS re-rendered: nothing was filed, and leaving it
    quoting a SKU that no longer exists only hides it from search.

    Only order-derived lines carry a SKU — purchase lines are named from the
    goods-receipt form and store no variant — so nothing else needs redoing.

    Returns (updated_count, skipped_invoice_ids).
    """
    from .models import InvoiceItem

    if not variant or not variant.pk:
        return 0, []

    updated, skipped = 0, []
    rows = (InvoiceItem.objects
            .filter(variant_id=variant.pk)
            .exclude(order_item=None)
            .select_related("invoice", "order_item", "order_item__product",
                            "order_item__product_variant"))
    for row in rows:
        inv = row.invoice
        if inv is None or inv.status == "draft":
            continue
        if inv.earsiv_uuid:
            if inv.pk not in skipped:
                skipped.append(inv.pk)
            continue
        desc = _invoice_line_desc(row.order_item)
        if desc != row.description:
            row.description = desc
            row.save(update_fields=["description"])
            updated += 1
    return updated, skipped


def sync_invoice_for_order(order):
    """Re-align a live order-attached invoice with its order.

    The account, the invoice and the order screen must show the same
    number. post_order_movement already re-posts the cari the moment an
    OrderItem changes, but the invoice was cut once and never looked
    again: editing order #136 from 419.20 m to 416.09 m moved the cari
    to 1486.48 and left invoice FAT-2026-000008 sitting at 1486.75.

    Rewrites the invoice's lines from the order's (updating matched
    lines in place so their ids survive), recomputes the totals and
    resyncs the ledger row.

    Two invoices are deliberately left alone:
      * draft — nothing is posted yet; issue() builds its lines then.
      * e-Arşiv filed (earsiv_uuid set) — that document went to the tax
        authority and cannot be quietly rewritten. It needs a credit
        note, which is a human decision, so we return it untouched for
        the caller to surface rather than silently diverging.

    Returns the Invoice it synced, or None.
    """
    from .models import Invoice, InvoiceItem

    if not order or not order.pk:
        return None
    inv = order.invoices.exclude(status="cancelled").order_by("-id").first()
    if inv is None or inv.status == "draft" or inv.earsiv_uuid:
        return None

    qty_map = order.get_billable_line_quantities()
    with transaction.atomic():
        kept, line_no = [], 0
        for it in order.items.all():
            qty = qty_map.get(it.pk, it.quantity or Decimal("0"))
            if not qty or qty <= 0:
                continue
            line_no += 1
            row = InvoiceItem.objects.filter(invoice=inv, order_item=it).first()
            if row:
                row.line_no = line_no
                row.quantity = qty
                row.unit_price = it.price or Decimal("0")
                row.description = _invoice_line_desc(it)
                row.save()
            else:
                row = InvoiceItem.objects.create(
                    invoice=inv, line_no=line_no,
                    product=it.product,
                    variant=getattr(it, "product_variant", None),
                    order_item=it,
                    description=_invoice_line_desc(it),
                    quantity=qty,
                    unit="mt",
                    unit_price=it.price or Decimal("0"),
                    discount_rate=Decimal("0"),
                    tax_rate=Decimal("0"),
                )
            kept.append(row.pk)
        # Lines deleted off the order come off the invoice too.
        InvoiceItem.objects.filter(invoice=inv).exclude(pk__in=kept).delete()
        inv.recompute_totals(save=True)
        inv.refresh_from_db()
        inv.resync_posted_movement()
    return inv


def create_invoice_for_order(order, *, user=None):
    """Auto-issue the sales invoice for a completed (shipped) order.

    Called from apply_order_status_change the moment an order enters a
    shipped status — the invoice is the paper trail of the completed
    sale. Lines mirror the order items at their ORDERED quantity
    (order.get_billable_line_quantities()), so the invoice, the cari and
    the order screen all state the same number. 0% tax so the invoice
    total equals order.billable_value(), i.e. exactly the receivable the
    order_sale movement already posted (issue() posts a 0-amount marker
    for order-linked invoices — no double counting). A line ordered at 0
    is skipped rather than invoiced as zero.

    Stays in step afterwards via sync_invoice_for_order, which re-aligns
    it whenever the order is edited.

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
    # CariAccount.book is null=False, so the account always states its
    # book and there is nothing to fall back to.
    book = cari.book
    settings_obj = CariSettings.for_book(book)
    member = getattr(user, "member", None) if user else None
    today = date.today()
    from datetime import timedelta
    term_days = cari.payment_term_days or 30

    qty_map = order.get_billable_line_quantities()

    with transaction.atomic():
        inv = Invoice.objects.create(
            cari=cari, book=book,
            series="INV",
            number=settings_obj.next_invoice_number(series="INV"),
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
            InvoiceItem.objects.create(
                invoice=inv, line_no=line_no,
                product=it.product,
                variant=getattr(it, "product_variant", None),
                order_item=it,
                description=_invoice_line_desc(it),
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

    The amount is order.billable_value() — price × ORDERED quantity per
    line (see Order.get_billable_line_quantities), i.e. the order total
    the order screen shows, whatever the warehouse has or hasn't
    scanned. Called both by the OrderItem save signal (order edits) and
    by every packing/reservation endpoint, so the cari matches the order
    from the moment it is saved.

    Idempotent: re-running after an edit updates the amount in place
    instead of creating a duplicate movement.
    """
    if not order or not order.pk:
        return None

    cari = order.cari
    if not cari:
        return None

    # The order total — see Order.billable_value().
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

    # The movement lives with the account it posts to, not with whoever
    # happens to be saving the order — a receivable in one book against
    # an account in another does not add up in either.
    book = cari.book
    currency = _resolve_currency(order)
    ref = order.order_number or f"ORD-{order.pk}"
    desc = f"Order #{order.pk}"

    if existing:
        # Update in place — keeps the movement's id stable and avoids
        # phantom rows in the ledger UI.
        existing.amount = total
        existing.currency = currency
        existing.book = book
        existing.date = order.order_date or (order.created_at.date() if order.created_at else date.today())
        existing.description = desc
        existing.reference = ref
        # Force amount_base recompute on save.
        existing.amount_base = Decimal("0")
        existing.save()
        return existing

    return CariMovement.objects.create(
        cari=cari,
        book=book,
        date=order.order_date or (order.created_at.date() if order.created_at else date.today()),
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
# movement, and nothing else.
#
# Completion used to also auto-collect the total, so the account netted
# to ~0 and read as a revenue journal. It double-collected any sale
# somebody had already recorded a collection for by hand — see
# post_retail_order_financials — and the automatic leg was removed
# rather than patched: retail collections are now entered by whoever
# took the money, like every other account's. The account therefore
# carries a real receivable, and a retail sale is only closed out once
# a collection is recorded against it.
#
# That cari IS the retail record — there is no second copy. Completion
# used to also mirror the sale into a separate "Perakende" accounting
# Book (EquityRevenue + its own till), which meant every walk-in sale
# was written twice in two places that could and did drift apart. The
# book, its till and its revenue rows were removed; read retail off the
# PERAKENDE cari and its statement.
# ---------------------------------------------------------------------------
RETAIL_CARI_CODE = "PERAKENDE"
_RETAIL_AUTO_DESC = "Perakende otomatik tahsilat"


def get_or_create_retail_cari(member=None) -> CariAccount:
    """The single shared cari all retail orders post to."""
    book = get_default_book(member)
    cari = CariAccount.objects.filter(book=book, code=RETAIL_CARI_CODE).first()
    if cari:
        return cari
    return CariAccount.objects.create(
        book=book, code=RETAIL_CARI_CODE, name="Perakende Satışları",
        type="customer", default_currency=_resolve_currency(),
        notes="Sistem carisi — anonim perakende satışlar otomatik buraya işlenir.",
        created_by=member,
    )


def post_retail_order_financials(order, user=None):
    """Completion posting for a retail order: attach the shared retail
    cari and post the order_sale movement. Idempotent — post_order_movement
    checks its own marker, so a re-ship after an un-ship writes nothing new.

    Collections are NOT posted here. Retail used to auto-collect the
    order total on completion so the account would net to ~0 and read as
    a revenue journal. It decided how much had already been collected by
    looking for payments whose `notes` was exactly "ORD-<pk>" — a tag only
    it ever wrote — so a collection entered by hand was invisible to it
    and the whole total got taken a second time. ORD-286 was collected
    57.00 by hand at 12:19 and another 57.01 automatically at 12:20,
    leaving the shared account reading "we owe the customer 57.01"; the
    cancelled TAH-015/016, TAH-017/018 and TAH-034/035 pairs on that
    statement are older instances of the same thing, cleaned up by hand.

    Retail collections are now recorded like every other account's: by
    the person who took the money. The consequence is deliberate — the
    PERAKENDE account no longer nets to zero on its own, and carries a
    real receivable until each sale is collected against.
    """
    member = getattr(user, "member", None) if user else None
    total = Decimal(str(order.billable_value() or 0))
    if total <= 0:
        return

    cari = get_or_create_retail_cari(member=member)
    if order.cari_id != cari.pk:
        order.cari = cari
        order.save(update_fields=["cari", "updated_at"])
    post_order_movement(order, member=member)


def reverse_retail_order_financials(order, user=None):
    """Undo post_retail_order_financials when a retail order leaves the
    shipped state (un-ship / cancel): remove the sale movement.

    Collections are left alone — every one of them is now somebody's
    hand-entered record of money that actually changed hands, and un-
    shipping an order does not un-receive it. Historical AUTO collections
    are still cleaned up, so un-shipping an order shipped before this
    change still reverses cleanly.
    """
    from .models import Payment

    reverse_order_movement(order)

    # The order already carries the retail cari that
    # post_retail_order_financials attached; ask it rather than guessing
    # which book to look in. A wrong guess found no account and silently
    # reversed nothing, leaving the collections standing on an un-shipped
    # order.
    cari = order.cari if order.cari_id else None
    if cari and cari.code == RETAIL_CARI_CODE:
        for pay in Payment.objects.filter(
                cari=cari, type="collection", status="confirmed",
                notes=f"ORD-{order.pk}",
                description__startswith=_RETAIL_AUTO_DESC):
            pay.cancel(user=user, reason="Sipariş sevk iptali")


# ---------------------------------------------------------------------------
# What a foreign-currency record converted at
# ---------------------------------------------------------------------------
def conversion_facts(obj):
    """The rate a record converted at and what it came to in base currency.

    Returns None when there is nothing worth stating — the record is
    already in the base currency, so a rate of 1 beside a repeated figure
    tells the reader nothing.

    The figures are read from the LEDGER ROW the record posted wherever
    there is one, not from the record's own fields. The row is what
    actually moved the balance, and the two genuinely can differ: a draft
    has posted nothing yet, and a rate corrected on a confirmed document
    only reaches the balance when it is resynced. Showing the document's
    intention while the ledger holds another number is how a page comes to
    disagree with the statement it is describing.

    Every model that carries money in a currency is handled by shape
    rather than by name, so a new one needs no change here:
      * a posted-movement link  → ask the movement (Payment, Invoice)
      * amount_base             → CariMovement
      * amount_in_base_currency → CashTransactionEntry
      * an exchange_rate alone  → compute, and say it is not posted yet
    """
    if obj is None:
        return None

    base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
    currency = getattr(obj, "currency", None)
    if currency is None or getattr(currency, "code", None) == base_code:
        return None

    from accounting.models import CurrencyCategory
    base = CurrencyCategory.objects.filter(code=base_code).first()

    def facts(rate, base_amount, posted):
        if rate is None:
            return None
        return {
            "currency": currency,
            "rate": Decimal(str(rate)),
            "base_amount": base_amount,
            "base_code": base_code,
            "base_symbol": (base.symbol if base else "") or base_code,
            # False means the figure is what the ledger holds; True means
            # it is what this record would post if it were.
            "pending": posted is False,
        }

    # A document that posted a ledger row — the row is the authority.
    movement = getattr(obj, "posted_movement", None)
    if movement is not None:
        return facts(movement.exchange_rate, movement.amount_base, True)

    # The ledger rows themselves.
    if getattr(obj, "amount_base", None) is not None and hasattr(obj, "exchange_rate"):
        return facts(obj.exchange_rate, obj.amount_base, True)
    if getattr(obj, "amount_in_base_currency", None) is not None:
        return facts(obj.exchange_rate, obj.amount_in_base_currency, True)

    # Nothing posted yet. Say what it would convert at, and mark it so the
    # page can word it as a projection rather than a fact.
    rate = getattr(obj, "exchange_rate", None)
    amount = getattr(obj, "amount", None)
    if not rate:
        from accounting.services import get_exchange_rate
        rate = get_exchange_rate(
            currency.code, base_code, on_date=getattr(obj, "date", None)
        )
    if not rate:
        return None
    base_amount = None
    if amount is not None:
        base_amount = (Decimal(amount) * Decimal(str(rate))).quantize(Decimal("0.01"))
    return facts(rate, base_amount, False)
