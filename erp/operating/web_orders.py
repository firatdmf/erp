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


def customer_for_order(web_client, price_currency):
    """(contact, current account, currency) for a new web order.

    The currency is the one the website priced the lines in, not the
    account's own: an order is priced in what was agreed, and the lines
    carry the website's numbers."""
    book = get_default_book()
    contact = contact_for(web_client, book)
    account = get_or_create_current_account_for_contact(contact, book=book)
    currency = (CurrencyCategory.objects.filter(code=(price_currency or "USD").upper()).first()
                or account.default_currency)
    return contact, account, currency
