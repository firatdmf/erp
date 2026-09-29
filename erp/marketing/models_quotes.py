"""Quotes — a price given to a customer before there is an order.

A quote is a sales document, so it lives with the catalog it prices
from rather than with the orders and warehouses in operating. Nothing
here touches stock or the ledger — the order a quote may become is made
from it in one step (views_quotes.quote_convert) once the customer says
yes, and that order is operating's like any other.
"""
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Quote(models.Model):
    """What we offered a customer: lines, prices, how long the offer
    stands. Nothing here touches stock or the ledger — a quote is a
    document, and the order it may become is made from it in one step
    (views_quotes.quote_convert) once the customer says yes.

    A quote can name a CRM contact or company, or just a name and a
    phone for someone not in the CRM yet; converting it needs the CRM
    customer, because the order's account does."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("accepted", _("Accepted")),
        ("declined", _("Declined")),
    ]

    number = models.CharField(max_length=30, unique=True, blank=True,
                              help_text="QUO-2026-000001")
    book = models.ForeignKey(
        "accounting.Book", on_delete=models.PROTECT, null=True, blank=True,
        related_name="quotes",
    )
    contact = models.ForeignKey("crm.Contact", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="quotes")
    company = models.ForeignKey("crm.Company", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="quotes")
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    currency = models.ForeignKey(
        "accounting.CurrencyCategory", on_delete=models.PROTECT, null=True, blank=True,
        related_name="quotes",
    )
    date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft", db_index=True)
    # Printed on the quote — terms, lead time, what the price includes.
    notes = models.TextField(blank=True)
    # For the team only: shown on the quote page, never printed. Carried to
    # the order the quote becomes.
    internal_notes = models.TextField(blank=True, default="")
    order = models.ForeignKey("operating.Order", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="quotes")
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="quotes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self):
        return self.number or f"Quote #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.number:
            # The order counter, so QUO- and ORD- numbers come from the one
            # sequence. Imported here: operating.models imports this app.
            from operating.models import OrderNumberSequence
            self.number = OrderNumberSequence.take("QUO")
        super().save(*args, **kwargs)

    def get_client(self):
        if self.company_id:
            return self.company.name
        if self.contact_id:
            return self.contact.name
        return self.customer_name or "—"

    @property
    def customer_type(self):
        return "company" if self.company_id else ("contact" if self.contact_id else "")

    def total(self):
        return sum((it.line_total() for it in self.items.all()), Decimal("0"))

    @property
    def is_expired(self):
        return (self.status in ("draft", "sent") and self.valid_until is not None
                and self.valid_until < timezone.localdate())

    @property
    def status_key(self):
        return "expired" if self.is_expired else self.status

    def status_label(self):
        return _("Expired") if self.is_expired else self.get_status_display()

    @property
    def can_edit(self):
        return self.status in ("draft", "sent")

    def conversion_blockers(self):
        """Why this quote can't become an order yet — empty when it can."""
        why = []
        if self.status not in ("draft", "sent"):
            why.append(_("Only an open quote can become an order."))
        if not (self.contact_id or self.company_id):
            why.append(_("Pick a CRM customer — the order's account needs one."))
        items = list(self.items.all())
        if not items:
            why.append(_("The quote has no lines."))
        free = [it.label() for it in items if not it.product_id]
        if free:
            why.append(_("These lines name no catalog product: %(lines)s")
                       % {"lines": ", ".join(free)})
        stale = [link for link in self.roll_links() if link.state != "free"]
        if stale:
            shown = ", ".join(link.barcode or "?" for link in stale[:10])
            if len(stale) > 10:
                shown += " …"
            why.append(_("%(n)s quoted rolls are no longer free — edit the quote to "
                         "drop or replace them: %(rolls)s") % {"n": len(stale), "rolls": shown})
        return why

    def roll_links(self):
        """Every roll quoted on this quote, each with how much of it is
        free right now (`available`), whether that still covers what was
        quoted (`state`), and which orders hold it (`held_by`). Free means
        on the shelf and not reserved for an order — the same measure the
        order form's roll list uses. Two queries for the whole quote."""
        from django.db.models import Sum
        from operating.models import OrderStockReservation

        links = list(QuoteItemRoll.objects.filter(quote_item__quote=self)
                     .select_related("stock_item__product__warehouse__accounting_book"))
        roll_ids = [link.stock_item_id for link in links if link.stock_item_id]
        reserved, held_by = {}, {}
        for sid, qty, number in (OrderStockReservation.objects
                                 .filter(stock_item_id__in=roll_ids, consumed=False)
                                 .values_list("stock_item_id", "quantity", "order__order_number")):
            reserved[sid] = reserved.get(sid, Decimal("0")) + (qty or Decimal("0"))
            held_by.setdefault(sid, []).append(number or "?")
        for link in links:
            roll = link.stock_item
            link.book = roll.product.warehouse.accounting_book if roll is not None else None
            if roll is None or roll.status == "consumed":
                link.available, link.state, link.held_by = Decimal("0"), "gone", ()
                continue
            phys = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
            free = (phys or Decimal("0")) - reserved.get(roll.pk, Decimal("0"))
            link.available = free if free > 0 else Decimal("0")
            link.held_by = tuple(held_by.get(roll.pk, ()))
            link.state = ("free" if link.available >= link.quantity else
                          "short" if link.available > 0 else "gone")
        return links

    @property
    def can_convert(self):
        return not self.conversion_blockers()


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name="items", on_delete=models.CASCADE)
    line_no = models.PositiveIntegerField(default=1)
    product = models.ForeignKey("marketing.Product", on_delete=models.SET_NULL, null=True, blank=True)
    product_variant = models.ForeignKey("marketing.ProductVariant", on_delete=models.SET_NULL,
                                        null=True, blank=True)
    # What is quoted when no catalog product is (or to say more about one).
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit = models.CharField(max_length=20, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["line_no", "pk"]

    def label(self):
        if self.product_variant_id:
            return f"{self.product_variant.product.title} [{self.product_variant.variant_sku}]"
        if self.product_id:
            return self.product.title
        return self.description or _("Line %(n)s") % {"n": self.line_no}

    def sku(self):
        if self.product_variant_id:
            return self.product_variant.variant_sku
        if self.product_id:
            return self.product.sku or ""
        return ""

    def line_total(self):
        return (self.quantity or Decimal("0")) * (self.price or Decimal("0"))


class QuoteItemRoll(models.Model):
    """One physical roll offered on a quote line — the barcode the
    customer is being quoted, not a hold on it. A quote may sit for weeks
    and most never become orders, so linking a roll here reserves
    nothing: the roll stays free for any order to take, and the quote
    says so when one has (see Quote.roll_links). The order a quote
    becomes is what reserves them."""

    quote_item = models.ForeignKey(QuoteItem, related_name="rolls", on_delete=models.CASCADE)
    # SET_NULL: a roll deleted from the warehouse leaves its barcode on the
    # quote, marked gone, rather than silently shrinking the line.
    stock_item = models.ForeignKey("operating.WarehouseProductItem", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="quote_links")
    barcode = models.CharField(max_length=64, blank=True)
    # How much of the roll is quoted, in the product's unit — all of what
    # was free when it was picked, unless cut down on the form.
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    # Filled in by Quote.roll_links(), which reads every roll's standing
    # in one pass.
    available = None
    state = None          # "free" | "short" | "gone"
    held_by = ()          # order numbers holding the roll now
    book = None           # the book whose shelf the roll stands on
