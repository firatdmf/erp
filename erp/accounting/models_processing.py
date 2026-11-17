"""Our own stock sent to a supplier to be worked on, on a purchase.

Crystals or pearls put on a plain fabric, embroidery, printing, dyeing: the
supplier is paid for the work, by the unit the goods are sold in, and the
same roll comes back as another variant. It is a purchase like any other
(the supplier's account, the price, receiving), except that a processing
line brings in no new stock: it names one of our rolls and what that roll
becomes.

  saved (draft)  the roll is away: still ours and still in the stock value,
                 but no order can pick it and the storefront doesn't offer it
                 (WarehouseProductItem.processing_line points here).
  received       the roll is moved onto the variant it became, in the same
                 warehouse, and its unit cost rises by the price of the work.
                 The supplier is owed meters × price, against Inventory —
                 the same figure the roll's value went up by.
  undone         the roll goes back to the variant and the cost it had.

The line keeps what is needed to put the roll back, and what was sent, if
the roll itself is later cut or deleted.
"""
from decimal import Decimal

from django.db import models


class ProcessingLine(models.Model):
    class Meta:
        ordering = ["invoice", "pk"]

    invoice = models.ForeignKey(
        "accounting.Invoice", on_delete=models.CASCADE, related_name="processing_lines")
    # SET_NULL: the original purchase can be cancelled, taking the roll with
    # it. What was sent stays on this row.
    stock_item = models.ForeignKey(
        "operating.WarehouseProductItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processing_history")
    barcode = models.CharField(max_length=64, blank=True)
    # What it is now, and what it becomes.
    from_variant = models.ForeignKey(
        "marketing.ProductVariant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    to_variant = models.ForeignKey(
        "marketing.ProductVariant", on_delete=models.PROTECT, related_name="processing_lines")
    # What the supplier works on and bills: what was left on the roll when
    # it was sent, in the unit the product is sold in.
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20, default="m")
    # Per unit, in the purchase's currency, as typed.
    unit_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="USD")

    # Set on receipt, cleared on undo.
    received_at = models.DateTimeField(null=True, blank=True)
    # Where the roll stood and what it cost before, for an undo to put back.
    from_product = models.ForeignKey(
        "operating.WarehouseProduct", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    unit_cost_before = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    # What the work added to one unit, in the book's base currency.
    added_cost_base = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    invoice_item = models.ForeignKey(
        "accounting.InvoiceItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processing_lines")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_received(self):
        return self.received_at is not None

    def __str__(self):
        return f"{self.barcode} → {self.to_variant_id} ({self.quantity} × {self.unit_price})"
