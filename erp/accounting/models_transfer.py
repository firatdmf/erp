"""Goods handed from one book to another, at what they cost.

A book is a business, and the rolls on its shelves are its asset. Carrying
a roll from Ergene's warehouse to Laleli's hands that asset over, so it
cannot be a warehouse move: both balance sheets would change with nothing
in either ledger to say why (see warehouse_roll_move_here, which refuses).

A transfer is the document that says why. It is one event with a half in
each book:

  the receiving book  gets an ordinary purchase, on its inter-company
                      account for the sender, priced at the sender's cost.
                      The rolls stand behind that purchase's lines, so its
                      stock and its debt are the ones every other purchase
                      has.

  the sending book    is owed the same amount by the inter-company mirror
                      (services_mirror), which parks it in Inter-company
                      Clearing; this document takes the goods off the
                      shelves against that same line. At cost there is no
                      sale and no profit — stock became a receivable.

The lines keep what the sender gave up: which rolls, how many meters, at
what unit cost, and where each came from. That is what an undo puts back,
and it does not change if the receiving book later edits its stock.
"""
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from authentication.models import Member


class StockTransfer(models.Model):
    class Meta:
        ordering = ["-date", "-pk"]

    from_warehouse = models.ForeignKey(
        "operating.Warehouse", on_delete=models.PROTECT, related_name="transfers_out")
    to_warehouse = models.ForeignKey(
        "operating.Warehouse", on_delete=models.PROTECT, related_name="transfers_in")
    # The books the two warehouses belonged to on the day. Kept rather than
    # read through the warehouse: the entries were posted in these.
    from_book = models.ForeignKey(
        "accounting.Book", on_delete=models.PROTECT, related_name="stock_transfers_out")
    to_book = models.ForeignKey(
        "accounting.Book", on_delete=models.PROTECT, related_name="stock_transfers_in")
    date = models.DateField()

    # The receiving book's half. Its total is what the sender is owed.
    purchase = models.OneToOneField(
        "accounting.Invoice", on_delete=models.PROTECT, related_name="stock_transfer")
    # What left the sender's shelves: meters times unit cost, summed and
    # not rounded, the way stock is valued (JournalLine.debit).
    value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    note = models.CharField(max_length=300, blank=True)

    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_stock_transfers")
    created_at = models.DateTimeField(auto_now_add=True)
    # An undone transfer stays as a record of what was done and taken back;
    # it stands in no ledger and holds no stock.
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="undone_stock_transfers")

    @property
    def number(self):
        return f"TRF-{self.pk:06d}" if self.pk else ""

    @property
    def is_undone(self):
        return self.undone_at is not None

    def __str__(self):
        return f"{self.number} {self.from_warehouse} → {self.to_warehouse}"


class StockTransferLine(models.Model):
    class Meta:
        ordering = ["sku", "barcode", "pk"]

    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="lines")
    # SET_NULL: the receiving book may sell the roll out and tidy it away;
    # what was transferred is on this row either way.
    stock_item = models.ForeignKey(
        "operating.WarehouseProductItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transfer_lines")
    barcode = models.CharField(max_length=64, blank=True)
    sku = models.CharField(max_length=128, blank=True)
    name = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=6)

    # Where the roll stood before, for an undo to put it back.
    source_product = models.ForeignKey(
        "operating.WarehouseProduct", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    source_purchase_item = models.ForeignKey(
        "accounting.InvoiceItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")

    @property
    def value(self):
        return Decimal(self.quantity or 0) * Decimal(self.unit_cost or 0)

    def __str__(self):
        return f"{self.barcode} {self.quantity} × {self.unit_cost}"
