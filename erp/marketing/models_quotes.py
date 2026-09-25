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
        return why

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
