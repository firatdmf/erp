"""Samples given to clients: the single cut, and the package of several.

A sample is not an order: nothing is billed and nothing is shipped against a
document. It is a cut taken off a stock item for somebody, recorded on that
item as a stock-out with purpose "sample" and the CRM record it went to.
One cut can be made from the item's own edit box (WarehouseRollEdit);
several sent together are a SamplePackage, made from the client's page.

Either way each piece is one StockMovement, valued at its own item and
posted to marketing expenses (services_posting.lines_for_stock_movement).
This module makes packages and reads the history back for the page the
client is looked at on.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import (Carrier, SamplePackage, StockMovement, WarehouseProduct,
                     WarehouseProductItem)


class PackageError(ValueError):
    """A sample package that cannot be made as asked. Nothing was written."""


def sample_client(client_type, client_pk):
    """(contact, company) for what the client picker posted, or (None, None).

    One of the two is set, never both: the picker offers contacts and
    companies in one list and the pick is one row of it."""
    from crm.models import Company, Contact

    try:
        pk = int(client_pk)
    except (TypeError, ValueError):
        return None, None
    if client_type == "contact":
        return Contact.objects.filter(pk=pk).first(), None
    if client_type == "company":
        return None, Company.objects.filter(pk=pk).first()
    return None, None


def _quantity(value):
    try:
        return Decimal(str(value if value not in (None, "") else "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


@transaction.atomic
def create_package(*, contact=None, company=None, lines, date=None, note="",
                   carrier="", tracking_number="", sent=False, user=None):
    """Make a package of samples for one client and take each piece off its item.

    `lines` is [{"stock_item_id": ..., "quantity": ...}]. All of it or none:
    a piece that cannot be cut — an item that is gone, more than is left on
    it — refuses the whole package, so what the client's page says they were
    sent is never half of what was put in the parcel.

    The stock leaves here, when the package is made. `sent` and the carrier
    only say where the parcel has got to.
    """
    from .views_warehouse import _record_stock_out

    client = contact or company
    if client is None:
        raise PackageError(_("Choose the client the sample went to."))

    # One line per item: the same roll named twice is one cut of the total.
    wanted = {}
    for line in lines or []:
        try:
            item_id = int(line.get("stock_item_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        wanted[item_id] = wanted.get(item_id, Decimal("0")) + _quantity(line.get("quantity"))
    if not wanted:
        raise PackageError(_("Add at least one item to the package."))

    rolls = {r.pk: r for r in (WarehouseProductItem.objects.select_for_update()
                               .filter(pk__in=wanted))}
    for item_id, quantity in wanted.items():
        roll = rolls.get(item_id)
        if roll is None:
            raise PackageError(_("An item on the package no longer exists — search for it again."))
        left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
        left = left or Decimal("0")
        label = roll.barcode or f"#{roll.pk}"
        if quantity <= 0:
            raise PackageError(_("%(item)s: enter how much is taken.") % {"item": label})
        if quantity > left:
            raise PackageError(_("%(item)s: only %(left)s is left on it.")
                               % {"item": label, "left": f"{left:.2f}"})

    package = SamplePackage.objects.create(
        contact=contact, company=company,
        date=date or timezone.localdate(),
        note=(note or "").strip()[:255],
        carrier=Carrier.resolve(carrier, user=user) or "",
        tracking_number=(tracking_number or "").strip()[:100],
        status="sent" if sent else "prepared",
        shipped_at=(date or timezone.localdate()) if sent else None,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    # One instance per product: two rolls of the same product both come off
    # its total, and a second copy would write its own stale figure back
    # over the first cut.
    products = {p.pk: p for p in (WarehouseProduct.objects.select_for_update()
                                  .filter(pk__in={r.product_id for r in rolls.values()}))}
    for item_id, quantity in wanted.items():
        roll = rolls[item_id]
        _record_stock_out(
            products[roll.product_id], roll, quantity, purpose="sample",
            reference=client.name, note=package.note, user=user,
            contact=contact, company=company, package=package)
    return package


def set_package_shipping(package, *, carrier="", tracking_number="", status=None, user=None):
    """Record where a package has got to. Moves no stock."""
    package.carrier = Carrier.resolve(carrier, user=user) or ""
    package.tracking_number = (tracking_number or "").strip()[:100]
    if status in dict(SamplePackage.STATUS_CHOICES):
        package.status = status
    if package.status == "prepared":
        package.shipped_at = None
    elif package.shipped_at is None:
        package.shipped_at = timezone.localdate()
    package.save(update_fields=["carrier", "tracking_number", "status", "shipped_at"])
    return package


def samples_sent(*, contact=None, company=None, limit=50):
    """The samples this client was given, newest first.

    A company's list includes what went to its people: a sample handed to
    the buyer is a sample the company has, and the company's page is where
    someone deciding what to show them next will look.

    Each row carries `.sample_note`, what was typed beside the pick.
    """
    samples = StockMovement.objects.filter(movement_type="out", purpose="sample")
    if contact is not None:
        samples = samples.filter(contact=contact)
    elif company is not None:
        samples = samples.filter(Q(company=company) | Q(contact__company=company))
    else:
        return []
    rows = list(samples.select_related("product__warehouse", "stock_item", "contact",
                                       "created_by", "sample_package")
                .order_by("-created_at", "-id")[:limit])
    for row in rows:
        # The reason is stored as "Sample for <client> — <note>"; the client
        # is the page being read, so only the note is worth repeating.
        _head, sep, note = (row.reason or "").partition(" — ")
        row.sample_note = note if sep else ""
    return rows


def sample_history(samples):
    """`samples` gathered into what was sent together.

    A list, newest first, of {"package": SamplePackage or None, "items": [...]}.
    A package's pieces sit under it; a cut made on its own is an entry of
    one with no package.
    """
    history, by_package = [], {}
    for sample in samples:
        package = sample.sample_package
        if package is None:
            history.append({"package": None, "items": [sample]})
        elif package.pk in by_package:
            by_package[package.pk]["items"].append(sample)
        else:
            entry = {"package": package, "items": [sample]}
            by_package[package.pk] = entry
            history.append(entry)
    return history


def sample_card_context(*, contact=None, company=None):
    """What the client page's Samples card draws itself from."""
    samples = samples_sent(contact=contact, company=company)
    return {
        "samples": samples,
        "sample_history": sample_history(samples),
        "sample_carriers": Carrier.choices(),
        "sample_statuses": SamplePackage.STATUS_CHOICES,
    }
