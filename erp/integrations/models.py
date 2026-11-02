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

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book} · Etsy {self.shop_name or self.shop_id or '(not connected)'}"

    @property
    def is_connected(self):
        return bool(self.shop_id and self.refresh_token)
