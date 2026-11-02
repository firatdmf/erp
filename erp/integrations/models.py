from django.conf import settings
from django.db import models


class EtsyConnection(models.Model):
    """One book's Etsy shop: who signed in, and where its sales are recorded.

    A book has at most one shop, and a shop belongs to one book: what Etsy
    sells comes off that book's shelves and is owed to it by Etsy, so the
    connection says which warehouse, which current account and which owner
    — nothing about any shop is written into the code.

    The tokens are the shop owner's sign-in, read-only. They are kept
    encrypted (integrations.etsy_api.seal/unseal) so the database never
    holds them in the clear; the app's own keystring and shared secret are
    not here at all but in settings.
    """

    book = models.OneToOneField("accounting.Book", on_delete=models.CASCADE,
                                related_name="etsy_connection")

    # The shop, as Etsy answered when it was connected.
    shop_id = models.BigIntegerField(null=True, blank=True)
    shop_name = models.CharField(max_length=255, blank=True, default="")
    etsy_user_id = models.BigIntegerField(null=True, blank=True)

    # Sealed — never read these columns directly; see etsy_api.
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.CharField(max_length=255, blank=True, default="")

    connected_at = models.DateTimeField(null=True, blank=True)
    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="+")

    # Where its sales are recorded.
    warehouse = models.ForeignKey("operating.Warehouse", on_delete=models.PROTECT,
                                  null=True, blank=True, related_name="+",
                                  help_text="The shelves Etsy orders are picked from.")
    current_account = models.ForeignKey("accounting.CurrentAccount", on_delete=models.PROTECT,
                                        null=True, blank=True, related_name="+",
                                        help_text="Etsy's account: sales, its fees and payouts.")
    fee_category = models.ForeignKey("accounting.ExpenseCategory", on_delete=models.PROTECT,
                                     null=True, blank=True, related_name="+",
                                     help_text="The expense category Etsy's fees go under.")
    payout_member = models.ForeignKey("authentication.Member", on_delete=models.PROTECT,
                                      null=True, blank=True, related_name="+",
                                      help_text="Who the payouts to the bank are paid to, as dividends.")

    # The sync. Off until someone switches it on, and then it records only
    # what Etsy shows from that moment: earlier months are recorded by hand.
    sync_from = models.DateTimeField(null=True, blank=True,
                                     help_text="Etsy orders and ledger entries from this moment on are recorded.")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book} · Etsy {self.shop_name or self.shop_id or '(not connected)'}"

    @property
    def is_syncing(self):
        return bool(self.is_connected and self.sync_from)

    def missing_settings(self):
        """The settings the sync cannot record without, by their labels."""
        return [label for field, label in (
            ("warehouse_id", "warehouse"), ("current_account_id", "Etsy's account"),
            ("fee_category_id", "fee category"), ("payout_member_id", "payouts go to"),
        ) if not getattr(self, field)]

    @property
    def is_connected(self):
        return bool(self.shop_id and self.refresh_token)


# What the sync did with each thing Etsy showed it, so nothing is recorded
# twice and whatever it could not record waits for a person. Only ids,
# amounts and labels are kept here — nothing about the buyer (Etsy's API
# terms): the buyer's name lives on the order's notes, as on any order.
RECORDED, COVERED, NEEDS_PERSON, HANDLED, SKIPPED = (
    "recorded", "covered", "needs_person", "handled", "skipped")
SYNC_STATES = [
    (RECORDED, "Recorded"),
    (COVERED, "Covered by an order"),
    (NEEDS_PERSON, "Needs a person"),
    (HANDLED, "Handled by a person"),
    (SKIPPED, "Skipped"),
]


class EtsyReceipt(models.Model):
    """One Etsy order, and the draft order it became."""

    connection = models.ForeignKey(EtsyConnection, on_delete=models.CASCADE, related_name="receipts")
    receipt_id = models.BigIntegerField()
    created = models.DateTimeField()
    state = models.CharField(max_length=16, choices=SYNC_STATES)
    order = models.ForeignKey("operating.Order", on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="+")
    problem = models.TextField(blank=True, default="")
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["connection", "receipt_id"],
                                               name="etsy_receipt_once")]
        ordering = ["-created"]


class EtsyLedgerEntry(models.Model):
    """One entry of the shop's payment account, and what it became."""

    connection = models.ForeignKey(EtsyConnection, on_delete=models.CASCADE, related_name="ledger_entries")
    entry_id = models.BigIntegerField()
    created = models.DateTimeField()
    ledger_type = models.CharField(max_length=64, blank=True, default="")
    reference_type = models.CharField(max_length=64, blank=True, default="")
    reference_id = models.CharField(max_length=64, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, blank=True, default="")
    kind = models.CharField(max_length=16)
    state = models.CharField(max_length=16, choices=SYNC_STATES)
    expense = models.ForeignKey("accounting.EquityExpense", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="+")
    dividend = models.ForeignKey("accounting.EquityDivident", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="+")
    problem = models.TextField(blank=True, default="")
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["connection", "entry_id"],
                                               name="etsy_ledger_entry_once")]
        ordering = ["-created", "-entry_id"]
