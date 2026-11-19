"""Our own rolls sent out to a supplier to be worked on, on a purchase.

Crystals or pearls put on a plain fabric, embroidery, printing, dyeing: a
purchase from that supplier lists our rolls going out ("goods out") beside
what comes back ("goods in", its ordinary products). The supplier is paid
the goods-in price, which is the work; the fabric was ours already.

  saved (draft)  each out roll is away: still ours and still valued, but no
                 order can pick it and the storefront doesn't offer it
                 (WarehouseProductItem.processing_line points here).
  received       a goods-in roll with an out roll's barcode IS that roll,
                 back as the variant and length it came in as; the other
                 out rolls were used up into what came in. Everything that
                 went out is pooled and spread per unit over everything
                 that came in, on top of each row's price.
  undone         every out roll is put back as it was, away again.

One line per out roll. It keeps what the roll was before it was settled,
so an undo can put it back, and what was sent if the roll itself is later
cut or deleted.
"""
from django.db import models


class ProcessingLine(models.Model):
    class Meta:
        ordering = ["invoice", "pk"]

    OUTCOMES = [
        ("came_back", "Came back"),
        ("used", "Used up"),
    ]

    invoice = models.ForeignKey(
        "accounting.Invoice", on_delete=models.CASCADE, related_name="processing_lines")
    # SET_NULL: the roll's own purchase can be cancelled, taking the roll
    # with it. What was sent stays on this row.
    stock_item = models.ForeignKey(
        "operating.WarehouseProductItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processing_history")
    # Goods counted in pieces go out in part: so many of a box. The part
    # sent is split off into an item of its own (stock_item), and this is
    # the box it came out of, which takes it back if it comes home unworked
    # (processing.save_draft_lines / release_lines). None when the whole
    # item went.
    split_from = models.ForeignKey(
        "operating.WarehouseProductItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    barcode = models.CharField(max_length=64, blank=True)
    # What was left on the roll when it was sent, in its product's unit.
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20, default="m")

    # Set on receipt, cleared on undo.
    received_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=10, choices=OUTCOMES, blank=True)
    # How long it came back, when it did.
    quantity_back = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    # The roll as it stood before receipt changed it, for an undo.
    from_product = models.ForeignKey(
        "operating.WarehouseProduct", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    unit_cost_before = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    length_before = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status_before = models.CharField(max_length=16, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_received(self):
        return self.received_at is not None

    def __str__(self):
        return f"{self.barcode} out on {self.invoice_id} ({self.quantity})"
