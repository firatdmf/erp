"""Who a storefront order is for, and which book it lands in.

An order's book is its current account's, so an order the website sent
with no customer behind it belonged to no book: no order list showed it,
and shipping it could post nothing. Web orders now come from a signed-in
customer only (create_web_order reads them off their token), and get a
customer the way an order typed in by hand does — a CRM contact and that
contact's current account.

Nobody is at the keyboard for a web order, so the book is the one the
ERP picks for any work without a member: get_default_book(), which reads
settings.CURRENT_ACCOUNT_BOOK_ID. The contact is made in that book's
directory, from the customer's own details.
"""
from accounting.models import CurrencyCategory
from accounting.services_accounts import (
    get_default_book, get_or_create_current_account_for_contact,
)
from crm.models import Contact, DuplicateName

NAME_MAX = Contact._meta.get_field("name").max_length


def contact_for(web_client, book):
    """The contact `web_client`'s orders are charged to in `book`'s
    directory, found or made — and remembered on the web client."""
    contact = web_client.contact
    if contact is not None and Contact.objects.of_book(book).filter(pk=contact.pk).exists():
        return contact

    email = (web_client.email or "").strip()
    contact = None
    if email:
        # Emails are stored as typed; the customer's may differ in case.
        contact = (Contact.objects.of_book(book)
                   .filter(email__overlap=list({email, email.lower()}))
                   .order_by("pk").first())
    if contact is None:
        contact = _new_contact(web_client, book, email)

    web_client.contact = contact
    web_client.save(update_fields=["contact"])
    return contact


def _new_contact(web_client, book, email):
    # A sign-up may give a business name and no person's name.
    company = ((web_client.web_client_settings or {}).get("company_name") or "").strip()
    name = (web_client.name or "").strip() or company or email or web_client.username
    fields = {
        "directory": book.directory,
        "email": [email] if email else [],
        "phone": [web_client.phone] if web_client.phone else [],
    }
    try:
        return Contact.objects.create(name=name[:NAME_MAX], **fields)
    except DuplicateName:
        # Somebody else in the directory already has this name. Matching on
        # a name alone would charge this order to a stranger, so the web
        # customer gets a contact of their own, which staff can merge if it
        # turns out to be the same person.
        suffix = f" (web #{web_client.pk})"
        return Contact.objects.create(name=name[:NAME_MAX - len(suffix)] + suffix, **fields)


def customer_for_order(web_client, price_currency, book=None):
    """(contact, current account, currency) for a new web order in `book`
    (the default book when none is given).

    The currency is the one the website priced the lines in, not the
    account's own: an order is priced in what was agreed, and the lines
    carry the website's numbers."""
    book = book or get_default_book()
    contact = contact_for(web_client, book)
    account = get_or_create_current_account_for_contact(contact, book=book)
    currency = (CurrencyCategory.objects.filter(code=(price_currency or "USD").upper()).first()
                or account.default_currency)
    return contact, account, currency


class WebOrderRefused(Exception):
    """A web order that cannot be placed as sent, said so before anything
    is written. `gone` names picked rolls no longer there as picked."""

    def __init__(self, message, gone=None):
        super().__init__(message)
        self.gone = gone or []


def lines_by_book(lines):
    """Where each line of a web order belongs: [(book, [(line, quantity,
    picks)])], the default book's first.

    `lines` are (item data, variant) pairs. Stock belongs to the book that
    owns its warehouse, so the lengths a customer cut from picked rolls go
    to theirs — a line whose rolls stand in two books' warehouses becomes a
    line in each. A line of "this many, you choose" goes to the one book whose
    warehouses the storefront offers it from; held in several, or in none,
    it goes to the default book, where staff pick it as before.

    Raises WebOrderRefused, naming them, when picked rolls are no longer
    there as picked: the customer was shown those rolls and is not sold
    fewer meters, or other rolls, without being asked."""
    from decimal import Decimal
    from . import storefront_stock

    default = get_default_book()
    groups = {default.pk: (default, [])}
    gone = []
    for data, variant in lines:
        asked = storefront_stock._requests(data.get("stock_items"))
        sku = variant.variant_sku if variant else ""
        if asked and sku:
            free = storefront_stock.offered(sku)
            by_book = {}
            for pk, quantity in asked.items():
                item, available = free.get(pk, (None, Decimal("0")))
                quantity = available if quantity is None else quantity
                # Cut as the cart said, which may no longer be possible:
                # the roll sold, or cut down to less than was asked.
                if item is None or not storefront_stock.can_cut(quantity, available):
                    gone.append(pk)
                    continue
                book = item.product.warehouse.accounting_book
                by_book.setdefault(book.pk, (book, []))[1].append((item, quantity))
            for book, rolls in by_book.values():
                total = sum((q for _item, q in rolls), Decimal("0"))
                groups.setdefault(book.pk, (book, []))[1].append((data, total, rolls))
            continue
        books = {item.product.warehouse.accounting_book for item, _available
                 in storefront_stock.offered(sku).values()} if sku else set()
        book = books.pop() if len(books) == 1 else default
        groups.setdefault(book.pk, (book, []))[1].append((data, None, []))
    if gone:
        raise WebOrderRefused("Some of the rolls in the cart are no longer available.", gone)
    lead = groups.pop(default.pk)
    rest = sorted(groups.values(), key=lambda pair: (pair[0].name or "", pair[0].pk))
    return ([lead] if lead[1] or not rest else []) + rest

