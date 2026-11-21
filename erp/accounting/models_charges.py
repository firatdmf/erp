"""What a purchase cost besides the goods, owed to whoever charged it.

The carrier who brought the delivery is the usual one: their invoice names
each purchase and what bringing it cost. That is owed to the carrier, not
to the supplier, so it is a payable on the carrier's own account, and it
is part of what the goods cost, so it is spread over the purchase's rolls
(accounting.purchase_charges).

A line is written with the purchase, draft or received, and posts only
while the purchase is received.
"""
from django.db import models


class PurchaseCharge(models.Model):
    class Meta:
        ordering = ["invoice", "position", "pk"]

    invoice = models.ForeignKey(
        "accounting.Invoice", on_delete=models.CASCADE, related_name="charges")
    position = models.PositiveSmallIntegerField(default=0)
    # Who is owed it. In the purchase's book; may be the supplier itself,
    # when they put the delivery on a bill of their own.
    current_account = models.ForeignKey(
        "accounting.CurrentAccount", on_delete=models.PROTECT, related_name="purchase_charges")
    description = models.CharField(max_length=200)
    # In the account's own currency: it is what we owe them.
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    # Their invoice's number, to match it to their statement.
    reference = models.CharField(max_length=60, blank=True, default="")
    # The payable, while the purchase is received.
    posted_movement = models.OneToOneField(
        "accounting.CurrentAccountMovement", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_charge")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} {self.amount} → {self.current_account_id}"

    @property
    def currency_code(self):
        from .services_accounts import invoice_currency_for
        return invoice_currency_for(self.current_account)
