"""
Current Account (Cari Hesap) module.

Phase 1: Core ledger primitives.
    - CariAccount    : Unified card per real-world counterparty (customer/supplier/both)
    - CariMovement   : Atomic ledger row. Balance = SUM(amount) per cari.
    - CariSettings   : Per-book counters & defaults (next code, next invoice no, etc.)

Phase 2: Invoicing.
    - Invoice        : Sales / purchase / return / proforma invoice header.
    - InvoiceItem    : Per-line item with quantity, price, KDV, discount.
                       Items recompute Invoice totals on save.
    - Issuing a non-draft, non-proforma invoice automatically creates a
      CariMovement.
    - Cancelling a posted invoice DELETES its CariMovement (terminal — no restore).

Phase 3: Payments (tahsilat / ödeme).
    - Payment           : Atomic money movement between Cari and a CashAccount.
    - PaymentAllocation : Optional M2M-style row linking the Payment to one or
                          more Invoices (partial / full / advance).
    - Confirming a Payment writes a CariMovement, updates the linked CashAccount
      balance, and recomputes paid_amount/status for each allocated Invoice.
    - Cancelling a Payment creates the inverse CariMovement, reverses the cash
      account update, and undoes the invoice allocations. Original rows are
      flagged 'cancelled' (audit-safe), not deleted.

Phase 5: Çek / Senet (check / promissory note).
    - CheckOrPromissoryNote: Portfolio-tracked negotiable instrument.
    - State machine:
          portfolio → endorsed | deposited | cleared | bounced | cancelled
          (received direction)
          portfolio → cleared | returned | cancelled
          (given direction)
    - Receiving a check from a customer creates a -X CariMovement (their balance
      shrinks as if a collection happened) but DOES NOT touch cash. Clearing it
      finally moves cash into a CashAccount. Bouncing reverses the cari side.
    - Endorsing transfers the obligation to another cari (+X on that cari).
    - Giving a check to a supplier creates +X on that cari (their owed-by-us
      shrinks). Cash only moves when the supplier deposits and it clears.

Sign cheat sheet (paired CariMovement + CashAccount delta):
    collection  (customer → us)    : CariMovement.amount = -X, cash += X
    payment     (us → supplier)    : CariMovement.amount = +X, cash -= X
    refund_in   (us → customer)    : CariMovement.amount = +X, cash -= X
    refund_out  (supplier → us)    : CariMovement.amount = -X, cash += X

Sign convention for CariMovement.amount:
    positive (+)  → cari owes us / we are owed money
                    (e.g., sales invoice issued, interest charged)
    negative (-)  → we owe cari / cari paid us
                    (e.g., collection received, purchase invoice from supplier,
                     refund issued by us)

CariAccount.cached_balance follows the same sign convention.

A movement is the only record of what an account is owed or owes. It used
to copy itself into the old AssetAccountsReceivable / LiabilityAccountsPayable
tables as well, for dashboards that have since been removed; those tables
are gone, and cached_balance is the single answer.
"""
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from authentication.models import Member
from crm.models import Company, Contact, Supplier

# Book and CurrencyCategory live in accounting/models.py, which imports THIS
# module at the end of its own body. Importing them by name here would be a
# circular import, so every FK to them is declared as a lazy "accounting.X"
# string reference instead.


# ---------------------------------------------------------------------------
# 1. CariAccount — the unified customer/supplier card
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _base_currency_symbol():
    """Symbol of the currency every stored balance is normalised to.

    Reads the same settings key _resolve_currency() uses, so there is one
    answer to "what is the base currency" rather than two that can drift.

    Cached because it is read once per row when a list of accounts renders.
    Falls back to the code, then to a bare "$", so a missing CurrencyCategory
    row degrades to a label rather than a 500.
    """
    from django.apps import apps  # resolved lazily — accounting.models
    # imports this module at the end of its own body, so a top-level import
    # of CurrencyCategory would be circular (same reason the FKs above are
    # declared as "accounting.X" strings).
    code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
    cur = (apps.get_model("accounting", "CurrencyCategory").objects
           .filter(code=code).first())
    if not cur:
        return "$"
    return cur.symbol or cur.code


class CariAccount(models.Model):
    class Meta:
        verbose_name = _("Current Account")
        verbose_name_plural = _("Current Accounts")
        unique_together = ("book", "code")
        indexes = [
            models.Index(fields=["book", "is_active"]),
            models.Index(fields=["book", "type"]),
        ]
        constraints = [
            # At most one cari per (book, contact/company/supplier).
            # Partial unique indexes (Postgres-only — works on our stack).
            models.UniqueConstraint(
                fields=["book", "contact"], name="uniq_cari_book_contact",
                condition=models.Q(contact__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["book", "company"], name="uniq_cari_book_company",
                condition=models.Q(company__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["book", "supplier"], name="uniq_cari_book_supplier",
                condition=models.Q(supplier__isnull=False),
            ),
        ]

    TYPE_CHOICES = [
        ("customer", _("Customer")),
        ("supplier", _("Supplier")),
        ("both",     _("Customer & Supplier")),
        ("staff",    _("Staff")),
        ("other",    _("Other")),
    ]

    book = models.ForeignKey("accounting.Book", on_delete=models.CASCADE, related_name="cari_accounts")

    code = models.CharField(max_length=20, help_text="e.g., CARI-001")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="customer")

    # CRM links — at most ONE of contact/company/supplier per cari (enforced in clean()).
    # Foreign keys (not OneToOne) so a single CRM entity can have one cari PER BOOK.
    # Per-book uniqueness is enforced via the constraint in Meta below.
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cari_accounts",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cari_accounts",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cari_accounts",
    )

    # Tax info (TR — e-Arşiv hazır)
    tax_office      = models.CharField(max_length=100, blank=True)
    tax_number      = models.CharField(max_length=11,  blank=True, help_text="Tax Number (VKN)")
    identity_number = models.CharField(max_length=11,  blank=True, help_text="ID Number (TCKN)")

    # Billing address (may differ from CRM)
    billing_address = models.TextField(blank=True)
    billing_city    = models.CharField(max_length=100, blank=True)
    billing_country = models.CharField(max_length=50,  default="TR")
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=30, blank=True)

    # Commercial terms
    default_currency = models.ForeignKey(
        "accounting.CurrencyCategory",
        on_delete=models.PROTECT,
        related_name="cari_accounts",
    )
    payment_term_days = models.PositiveIntegerField(default=30, help_text="Payment term (days)")
    credit_limit      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_rate     = models.DecimalField(max_digits=5,  decimal_places=2, default=Decimal("0.00"),
                                            help_text="Customer-specific discount %")

    # Opening balance (carried forward from previous period)
    opening_balance      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    opening_balance_date = models.DateField(null=True, blank=True)

    # Cached aggregate — kept in step by recompute_balance(). A sum over
    # this account's live movements, in the base currency.
    #
    # There used to be a cached_balance_base beside it holding the SAME
    # number, set from the same expression, with the account list summing
    # one while filtering on the other. Two columns for one value is how
    # a balance and a statement came to disagree one level up; the
    # duplicate was dropped in migration 0087.
    cached_balance   = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    last_movement_at = models.DateTimeField(null=True, blank=True)

    # Meta
    is_active  = models.BooleanField(default=True)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_cari_accounts")

    def __str__(self):
        return f"{self.code} | {self.name}"

    def clean(self):
        super().clean()
        links = [bool(self.contact_id), bool(self.company_id), bool(self.supplier_id)]
        if sum(links) > 1:
            raise ValidationError(
                "An account can be linked to only one of Contact, Company or Supplier."
            )

    def recompute_balance(self, save=True):
        """Recalculate cached_balance from movements. Safe to call any time.

        BOTH figures are the base-currency (USD) sum. `amount` is whatever
        currency the movement was entered in, so adding it across movements
        only works while an account never mixes currencies — the moment one
        does, summing `amount` adds EUR to USD and produces a number that is
        not money at all. A 608.26 USD order settled by a 540 EUR collection
        read as a balance of 68.26 when the real position was -6.91.

        `amount_base` is that same movement normalised at its own recorded
        exchange rate, so summing it is meaningful whatever mix of currencies
        an account holds. For a USD-only account the two are identical (rate
        1.0), which is why this changes nothing for almost every account.

        Voided rows are excluded, via the same .live() the statement uses.
        Both numbers therefore come from one rule instead of two that were
        only ever equal by argument.
        """
        # .live() — the same rule the statement asks, so the two can never
        # print different numbers for this account. See CariMovementQuerySet.
        agg = self.movements.live().aggregate(
            total_base=Sum("amount_base"),
            last=models.Max("created_at"),
        )
        self.cached_balance   = (agg["total_base"] or Decimal("0.00"))
        self.last_movement_at = agg["last"]
        if save:
            CariAccount.objects.filter(pk=self.pk).update(
                cached_balance=self.cached_balance,
                last_movement_at=self.last_movement_at,
            )
        return self.cached_balance

    @property
    def balance_label(self):
        if self.cached_balance > 0:
            return _("Owes Us")
        if self.cached_balance < 0:
            return _("We Owe")
        return _("Closed")

    @property
    def absolute_balance(self):
        return abs(self.cached_balance)

    @property
    def is_over_credit_limit(self):
        return self.credit_limit > 0 and self.cached_balance > self.credit_limit

    @property
    def display_currency_symbol(self):
        """Symbol for the figures shown beside it — the BASE currency.

        Every balance on this model (cached_balance, absolute_balance) is a
        base-currency sum, and credit_limit is compared against it directly in
        the over-limit filter, so all of them are USD regardless of which
        currency the account itself trades in. Returning default_currency here
        labelled a converted USD figure with the account's own symbol: the two
        TRY accounts rendered "₺47.73" for what is $47.73, having previously
        rendered "₺2,250.12" for the same position.

        Cached on the class — this runs once per row on a 50-row list page.
        """
        return _base_currency_symbol()


# ---------------------------------------------------------------------------
# 2. CariMovement — the atomic ledger row
# ---------------------------------------------------------------------------
class CariMovementQuerySet(models.QuerySet):
    """The one definition of which rows count.

    Balances and statements are two views of the same ledger, and they
    used to decide membership separately: recompute_balance summed EVERY
    row, while the statement re-derived "is this half of a cancelled
    document's pair?" from the documents themselves on each render. The
    two agreed only while the excluded set happened to sum to zero, and
    a deleted payment broke that — the statement closed 150.00 below the
    account page it belonged to, with nothing in the code able to notice.

    Membership is now a stored fact on the row (`is_void`) rather than a
    predicate recomputed from elsewhere, and both callers ask here. They
    cannot disagree, because there is only one answer.
    """

    def live(self):
        """Rows that count toward a balance — everything not voided."""
        return self.filter(is_void=False)

    def void(self):
        """Rows kept for history but excluded from every total."""
        return self.filter(is_void=True)


class CariMovement(models.Model):
    class Meta:
        verbose_name = _("Account Movement")
        verbose_name_plural = _("Account Movements")
        indexes = [
            models.Index(fields=["cari", "-date"]),
            models.Index(fields=["book", "due_date"]),
            models.Index(fields=["movement_type"]),
        ]
        ordering = ["-date", "-id"]

    MOVEMENT_TYPES = [
        ("opening",          _("Opening Balance")),
        ("order_sale",       _("Sales Order")),
        ("invoice_sale",     _("Sales Invoice")),
        ("invoice_purchase", _("Purchase Invoice")),
        ("return_sale",      _("Sales Return")),
        ("return_purchase",  _("Purchase Return")),
        ("collection",       _("Collection")),
        ("payment",          _("Payment")),
        ("advance_in",       _("Advance Received")),
        ("advance_out",      _("Advance Given")),
        ("interest",         _("Interest / Late Fee")),
        ("discount",         _("Discount")),
        ("adjustment",       _("Offset / Adjustment")),
        ("check_in",         _("Check/Note Received")),
        ("check_out",        _("Check/Note Given")),
        # Import markers, stamped by migration 0086's backfill on rows
        # carried over from the old system. Unrelated to the removed
        # AssetAccountsReceivable / LiabilityAccountsPayable tables, and
        # kept because live rows still carry them. Never user-picked —
        # see views_accounts._HIDDEN_MOVEMENT_TYPES.
        ("legacy_ar",        _("Legacy - Receivable")),
        ("legacy_ap",        _("Legacy - Payable")),
    ]

    cari     = models.ForeignKey(CariAccount, on_delete=models.CASCADE, related_name="movements")
    book     = models.ForeignKey("accounting.Book", on_delete=models.CASCADE, related_name="cari_movements")
    date     = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    amount        = models.DecimalField(max_digits=14, decimal_places=2)
    currency      = models.ForeignKey("accounting.CurrencyCategory", on_delete=models.PROTECT)
    # 8 decimals, not 6. A rate is only ever read back multiplied by an
    # amount, and 6 decimals quantise the PRODUCT: at 43,940 TRY one step
    # of the sixth decimal moves the base total by 4.4 cents, so $913.00
    # was simply not reachable — 912.99 and 913.03 were. Whoever typed the
    # figure they actually converted at watched it come back as a different
    # one. max_digits widens in step so the integer range is unchanged;
    # every rate on the book is below 1.0 in any case, since these are
    # stored as currency→base (TRY→USD ≈ 0.0208).
    exchange_rate = models.DecimalField(max_digits=16, decimal_places=8, default=Decimal("1.00000000"),
                                        help_text="Rate from movement currency to base (USD)")
    amount_base   = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"),
                                        help_text="Amount normalized to base currency (USD)")

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)

    source_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    source_id   = models.PositiveIntegerField(null=True, blank=True)
    source      = GenericForeignKey("source_type", "source_id")

    description = models.CharField(max_length=300, blank=True)
    reference   = models.CharField(max_length=50,  blank=True, help_text="Invoice no, check no, etc.")

    # Kept for history, excluded from every total. Set on both halves of
    # a cancelled document's pair — see CariMovementQuerySet. Stored
    # rather than derived so a balance and a statement cannot reach
    # different answers about the same row; migration 0086 backfills it
    # from the predicate the statement used to recompute per render.
    is_void = models.BooleanField(
        default=False, db_index=True,
        help_text="Excluded from balances and statements, but kept on the "
                  "record — one half of a cancelled document's pair.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_cari_movements")

    objects = CariMovementQuerySet.as_manager()

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.cari.code} | {self.date} | {sign}{self.amount} {self.currency.code}"

    def entered_rate(self):
        """A rate the document that posted this row says applies.

        The same precedence CashTransactionEntry.resolve_exchange_rate has
        always used, which this model was missing: whoever recorded the
        transaction was there, and a cash exchange at the döviz bürosu is
        not the mid-market rate. Without this the rate typed on the payment
        form reached the cash ledger and stopped — the cari movement went on
        converting at the published rate, so the figure the operator
        corrected was not the figure their balance moved by.

        Only documents that opt in are asked, via `ledger_exchange_rate()`.
        Merely HAVING an exchange_rate field is not enough to be consulted:
        Invoice's carries a default of 1.000000 and no view ever sets it, so
        reading that field would convert every foreign-currency invoice at
        par — which is the very confusion between "unset" and "one to one"
        that Payment.exchange_rate is nullable to avoid.

        Returns None for "nobody said", which is what lets the published
        rate apply instead.
        """
        if not (self.source_type_id and self.source_id):
            return None
        model = self.source_type.model_class()
        if model is None or not callable(getattr(model, "ledger_exchange_rate", None)):
            # Asked of the CLASS, so the common case — an invoice, an
            # order — costs no query at all.
            return None
        # Deliberately NOT self.source: the generic FK caches its target on
        # first access, and this method is what first accesses it. An edit
        # then re-saves the very same movement instance
        # (resync_posted_movement reuses payment.posted_movement), so the
        # cache would hand back the payment as it was BEFORE the new rate
        # was typed — and the correction would appear to save while the
        # balance kept the old figure.
        source = model.objects.filter(pk=self.source_id).first()
        if source is None:
            return None
        rate = source.ledger_exchange_rate()
        return Decimal(str(rate)) if rate else None

    def save(self, *args, **kwargs):
        base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
        if self.currency.code == base_code:
            self.exchange_rate = Decimal("1.000000")
            self.amount_base = self.amount.quantize(Decimal("0.01"))
        elif not self.amount_base:
            rate = self.entered_rate()
            if rate is None:
                from accounting.services import get_exchange_rate
                # The rate on the movement's own date — a backdated row is
                # worth what it was worth then.
                rate = get_exchange_rate(
                    self.currency.code, base_code, on_date=self.date
                ) or Decimal("1.000000")
            self.exchange_rate = Decimal(str(rate))
            self.amount_base = (self.amount * self.exchange_rate).quantize(Decimal("0.01"))

        if not self.book_id and self.cari_id:
            self.book_id = self.cari.book_id

        with transaction.atomic():
            super().save(*args, **kwargs)
            self.cari.recompute_balance(save=True)


# ---------------------------------------------------------------------------
# 3. CariSettings — per-book counters & defaults
# ---------------------------------------------------------------------------
class CariSettings(models.Model):
    class Meta:
        verbose_name = "Account Settings"
        verbose_name_plural = "Account Settings"

    book = models.OneToOneField("accounting.Book", on_delete=models.CASCADE, related_name="cari_settings")

    next_cari_seq    = models.PositiveIntegerField(default=1)
    next_invoice_seq = models.PositiveIntegerField(default=1)
    next_payment_seq = models.PositiveIntegerField(default=1)

    cari_code_prefix  = models.CharField(max_length=10, default="CARI")
    cari_code_padding = models.PositiveSmallIntegerField(default=3)

    default_tax_rate          = models.DecimalField(max_digits=5, decimal_places=2,
                                                    default=Decimal("20.00"))
    default_payment_term_days = models.PositiveIntegerField(default=30)
    default_currency = models.ForeignKey(
        "accounting.CurrencyCategory",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="cari_settings_default",
    )

    # Language the printable invoice DOCUMENT renders in (independent of
    # the UI language) — export invoices go out in English by default.
    INVOICE_LANGUAGE_CHOICES = [("en", "English"), ("tr", "Türkçe")]
    invoice_language = models.CharField(
        max_length=5, choices=INVOICE_LANGUAGE_CHOICES, default="en",
    )

    def __str__(self):
        return f"Cari Settings ({self.book.name})"

    def next_cari_code(self):
        """Generate next CARI code and bump the counter atomically."""
        with transaction.atomic():
            locked = CariSettings.objects.select_for_update().get(pk=self.pk)
            code = f"{locked.cari_code_prefix}-{str(locked.next_cari_seq).zfill(locked.cari_code_padding)}"
            locked.next_cari_seq += 1
            locked.save(update_fields=["next_cari_seq"])
            return code

    def next_invoice_number(self, series="INV"):
        """
        Generate the next invoice number using the brand prefix + 4-digit
        year + zero-padded sequence (e.g. KRV20250000013). Falls back to
        the dashed `INV-YEAR-NNNNNN` shape when no brand prefix is set
        (the default for the demfirat brand) so numbers stay readable.

        Counter is per book — all series share the same sequence so the
        number is globally unique within a book regardless of the
        invoice type.
        """
        from django.utils import timezone
        from django.conf import settings as _s

        with transaction.atomic():
            locked = CariSettings.objects.select_for_update().get(pk=self.pk)
            year = timezone.now().year
            seq = locked.next_invoice_seq
            prefix = getattr(_s, "BRAND_INVOICE_PREFIX", "").strip()
            if prefix:
                # Karven-style: KRV20250000013 (no dashes, 7-digit seq)
                number = f"{prefix}{year}{str(seq).zfill(7)}"
            else:
                # Legacy fallback so old fixtures / tests keep working.
                number = f"{series}-{year}-{str(seq).zfill(6)}"
            locked.next_invoice_seq += 1
            locked.save(update_fields=["next_invoice_seq"])
            return number

    @classmethod
    def for_book(cls, book):
        obj, _ = cls.objects.get_or_create(book=book)
        return obj


# ---------------------------------------------------------------------------
# 4. Invoice — Fatura
# ---------------------------------------------------------------------------
class Invoice(models.Model):
    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        unique_together = ("book", "series", "number")
        indexes = [
            models.Index(fields=["book", "-date"]),
            models.Index(fields=["cari", "-date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["-date", "-id"]

    INVOICE_TYPES = [
        ("sales",           _("Sales Invoice")),
        ("purchase",        _("Purchase Invoice")),
        ("sales_return",    _("Sales Return")),
        ("purchase_return", _("Purchase Return")),
        ("proforma",        _("Proforma")),
    ]
    STATUS_CHOICES = [
        ("draft",          _("Draft")),
        ("issued",         _("Issued")),
        ("partially_paid", _("Partially Paid")),
        ("paid",           _("Paid")),
        ("overdue",        _("Overdue")),
        ("cancelled",      _("Cancelled")),
    ]

    cari   = models.ForeignKey(CariAccount, on_delete=models.PROTECT, related_name="invoices")
    book   = models.ForeignKey("accounting.Book", on_delete=models.PROTECT, related_name="invoices")

    series = models.CharField(max_length=10, default="INV")
    number = models.CharField(max_length=30)
    type   = models.CharField(max_length=20, choices=INVOICE_TYPES, default="sales")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    date          = models.DateField()
    due_date      = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)

    # Optional link to an existing sales order
    order = models.ForeignKey(
        "operating.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoices",
    )

    currency      = models.ForeignKey("accounting.CurrencyCategory", on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6,
                                        default=Decimal("1.000000"))

    # ── Purchases: the two-step order → goods-receipt flow ────────────
    # A purchase is entered as a DRAFT order first (no stock, no debt) and
    # only becomes real stock when it is confirmed. These two fields are
    # what carries it across that gap; both stay set afterwards.
    #
    # intake_warehouse — the depot this purchase is (or was) received into.
    #   Previously re-derived from surviving rolls, which quietly made a
    #   purchase uneditable once its roll links were orphaned, and can't
    #   work at all for a draft that has no rolls yet.
    # intake_plan — the receipt exactly as the goods-receipt page posts it
    #   (products → variants → rolls, with the intended SKUs and any typed
    #   barcodes). Draft: this IS the document, replayed on confirm.
    #   Confirmed: kept as the record of what was received.
    intake_warehouse = models.ForeignKey(
        "operating.Warehouse", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_invoices",
    )
    intake_plan = models.JSONField(null=True, blank=True)

    # Totals (auto-recomputed from items)
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    other_charges   = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total           = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    # Payment tracking (set by allocations in Phase 3)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    balance     = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    # The CariMovement that posted this invoice to the ledger (set on issue()).
    # Cancellation DELETES the movement (SET_NULL clears this pointer).
    posted_movement = models.OneToOneField(
        CariMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice",
    )

    # e-Arşiv / e-Fatura integration placeholders
    earsiv_uuid    = models.CharField(max_length=50, blank=True)
    earsiv_status  = models.CharField(max_length=20, blank=True)
    earsiv_pdf_url = models.URLField(blank=True)

    # ── Consignee snapshot (overrides cari values on THIS invoice).
    # Blank → fall back to invoice.cari.* in the template. Letting
    # users edit these per-invoice means they can correct typos or
    # use a different shipping address without polluting the cari
    # master record.
    bill_to_name        = models.CharField(max_length=200, blank=True)
    bill_to_address     = models.TextField(blank=True)
    bill_to_city        = models.CharField(max_length=100, blank=True)
    bill_to_country     = models.CharField(max_length=50,  blank=True)
    bill_to_phone       = models.CharField(max_length=30,  blank=True)
    bill_to_email       = models.CharField(max_length=200, blank=True)
    bill_to_tax_office  = models.CharField(max_length=100, blank=True)
    bill_to_tax_number  = models.CharField(max_length=20,  blank=True)

    # ── Issuer snapshot (overrides BRAND_* settings on THIS invoice). #
    issuer_name        = models.CharField(max_length=200, blank=True)
    issuer_address     = models.TextField(blank=True)
    issuer_phone       = models.CharField(max_length=30,  blank=True)
    issuer_fax         = models.CharField(max_length=30,  blank=True)
    issuer_email       = models.CharField(max_length=200, blank=True)
    issuer_tax_office  = models.CharField(max_length=100, blank=True)
    issuer_tax_number  = models.CharField(max_length=20,  blank=True)

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_invoices")

    def __str__(self):
        return f"{self.display_number} | {self.cari.name} | {self.total} {self.currency.code}"

    # -- helpers -----------------------------------------------------------
    @property
    def issuer_display_name(self):
        """Who this invoice says it is from.

        Precedence: the per-invoice snapshot, then the issuing book's
        brand name, then the brand profile in settings.

        BRAND_LEGAL_SUFFIX is appended only to that last, settings-level
        fallback. A name typed on the invoice or on the book is taken as
        complete — otherwise a lockup like "DEMFIRAT® | Karven Home
        Collection" would print with a "SAN. TİC. LTD. ŞTİ." bolted onto
        the end of the marketing half of it.
        """
        from django.conf import settings
        explicit = (self.issuer_name or "").strip()
        if not explicit and self.book_id:
            explicit = (self.book.brand_name or "").strip()
        if explicit:
            return explicit
        base = getattr(settings, "BRAND_NAME", "") or "Nejum ERP"
        suffix = (getattr(settings, "BRAND_LEGAL_SUFFIX", "") or "").strip()
        return f"{base} {suffix}".strip() if suffix else base

    @property
    def display_number(self):
        """How this invoice is named on screen and in ledger descriptions.

        next_invoice_number() already bakes the series into the number
        ("FAT-2026-000071"), so the long-standing habit of rendering
        `series`-`number` printed it twice — "FAT-FAT-2026-000071", and
        once purchases were renamed, "Purchase-Purchase-2026-000072".

        Joining is kept as the fallback for rows whose number does NOT
        embed the series: hand-typed numbers, and the brand-prefix shape
        (BLN20260000013) used when BRAND_INVOICE_PREFIX is set."""
        num = (self.number or "").strip()
        series = (self.series or "").strip()
        if not num:
            return series
        if not series or num.upper().startswith(series.upper() + "-"):
            return num
        return f"{series}-{num}"

    @property
    def is_outgoing(self):
        """True for sales-side invoices (we send them to customer)."""
        return self.type in ("sales", "proforma", "purchase_return")

    @property
    def is_incoming(self):
        """True for purchase-side invoices (we receive them from supplier)."""
        return self.type in ("purchase", "sales_return")

    @property
    def ledger_sign(self):
        """
        Sign applied when posting to CariMovement.
            sales / proforma           → +  (cari owes us more)
            purchase                   → −  (we owe cari more)
            sales_return               → −  (we owe back to customer)
            purchase_return            → +  (supplier owes back to us)
        Proforma is excluded from posting at the call site, but kept here
        for completeness.
        """
        return +1 if self.type in ("sales", "proforma", "purchase_return") else -1

    @property
    def movement_type(self):
        return {
            "sales":           "invoice_sale",
            "purchase":        "invoice_purchase",
            "sales_return":    "return_sale",
            "purchase_return": "return_purchase",
            "proforma":        "invoice_sale",
        }[self.type]

    # -- totals ------------------------------------------------------------
    def recompute_totals(self, save=True):
        agg = self.items.aggregate(
            sub=Sum("subtotal"),
            disc=Sum("discount_amount"),
            tax=Sum("tax_amount"),
            tot=Sum("total"),
        )
        self.subtotal        = agg["sub"]  or Decimal("0.00")
        self.discount_amount = agg["disc"] or Decimal("0.00")
        self.tax_amount      = agg["tax"]  or Decimal("0.00")
        items_total          = agg["tot"]  or Decimal("0.00")
        self.total           = items_total + (self.other_charges or Decimal("0.00"))
        self.balance         = self.total - (self.paid_amount or Decimal("0.00"))
        if save:
            Invoice.objects.filter(pk=self.pk).update(
                subtotal=self.subtotal,
                discount_amount=self.discount_amount,
                tax_amount=self.tax_amount,
                total=self.total,
                balance=self.balance,
            )

    def recompute_payment(self, save=True):
        """
        Recalculate paid_amount, balance, and status from PaymentAllocations.
        Called after a Payment is confirmed/cancelled and after each allocation save.
        Does NOT touch status if invoice is draft/cancelled (those aren't 'payable').
        """
        agg = self.allocations.filter(payment__status="confirmed").aggregate(
            paid=Sum("amount"),
        )
        self.paid_amount = agg["paid"] or Decimal("0.00")
        self.balance     = self.total - self.paid_amount

        new_status = self.status
        if self.status not in ("draft", "cancelled"):
            if self.paid_amount <= Decimal("0"):
                new_status = "issued"
            elif self.balance <= Decimal("0.005"):  # rounded-zero
                new_status = "paid"
            else:
                new_status = "partially_paid"

        if save:
            Invoice.objects.filter(pk=self.pk).update(
                paid_amount=self.paid_amount,
                balance=self.balance,
                status=new_status,
            )
            self.status = new_status

    # -- lifecycle ---------------------------------------------------------
    def issue(self, user=None):
        """Draft → Issued.

        Sign / amount rules:
        - Standalone invoice (no linked order) → posts +/- total to the
          ledger. This invoice IS the financial event.
        - Invoice from an existing Order → posts amount = 0 to the
          ledger. The order_sale movement created when the order was
          placed already accounts for the receivable; we just want a
          row in the statement that says "Sales Invoice FAT-XXX
          issued" as a paper-trail marker, with no double counting.
        """
        if self.status not in ("draft",):
            raise ValidationError(f"Only draft invoices can be issued (current status: {self.status}).")
        if self.type == "proforma":
            # Proforma doesn't hit the ledger — only flips status
            self.status = "issued"
            self.save(update_fields=["status", "updated_at"])
            return None
        if not self.items.exists():
            raise ValidationError("Cannot issue an invoice with no items.")

        # An invoice raised against an order posts NOTHING. The order_sale
        # movement already carries the receivable, so this used to write a
        # 0.00 row purely to record that a document existed — a line on the
        # statement that could never explain how the balance got from the
        # row above it to the row below, which is the only job a statement
        # row has. Invoices are listed on the account page in their own
        # card, which is where "was this invoiced?" belongs.
        #
        # A STANDALONE invoice is a different animal and still posts: for a
        # purchase receipt or a sale with no order behind it, this movement
        # IS the debt and nothing else would create it.
        if self.order_id:
            self.status = "issued"
            self.save(update_fields=["status", "updated_at"])
            return None

        amount_signed = self.total * Decimal(self.ledger_sign)

        movement = CariMovement.objects.create(
            cari=self.cari,
            book=self.book,
            date=self.date,
            due_date=self.due_date,
            amount=amount_signed,
            currency=self.currency,
            movement_type=self.movement_type,
            description=f"{self.get_type_display()} {self.display_number}",
            reference=f"{self.display_number}",
            source_type=ContentType.objects.get_for_model(Invoice),
            source_id=self.pk,
            created_by=user.member if user and hasattr(user, "member") else None,
        )
        self.posted_movement = movement
        self.status = "issued"
        self.save(update_fields=["status", "posted_movement", "updated_at"])
        return movement

    def resync_posted_movement(self, user=None):
        """Refresh the ledger row after totals/date/currency change on an
        already-issued invoice. Order-attached invoices post no row at all
        (the order carries the receivable); standalone invoices get
        amount/desc/date refreshed in place on the SAME CariMovement
        (never delete+recreate — that would break anything referencing it
        by id).

        If `posted_movement` is somehow missing on a non-draft/non-cancelled
        invoice (should not happen in normal flow, since issue() always sets
        it in the same transaction as status→issued), post a fresh one
        instead of silently doing nothing — a purchase/sales edit that
        changes the total must never leave the cari balance stale.
        """
        if self.status in ("draft", "cancelled"):
            return None
        # Nothing to keep in step for an order-attached invoice — it posts
        # no row. Returning early matters as much as issue() not creating
        # one: the `mv is None` branch below exists to repost a movement
        # that went missing, and without this guard every edit would
        # resurrect exactly the 0.00 row we stopped writing.
        if self.order_id:
            return None

        amount = self.total * Decimal(self.ledger_sign)

        mv = self.posted_movement
        if mv is None:
            mv = CariMovement.objects.create(
                cari=self.cari, book=self.book, date=self.date, due_date=self.due_date,
                amount=amount, currency=self.currency, movement_type=self.movement_type,
                description=f"{self.get_type_display()} {self.display_number}",
                reference=f"{self.display_number}",
                source_type=ContentType.objects.get_for_model(Invoice),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )
            self.posted_movement = mv
            self.save(update_fields=["posted_movement", "updated_at"])
            return mv

        mv.amount = amount
        mv.amount_base = Decimal("0")    # force recompute on save
        mv.date = self.date
        mv.due_date = self.due_date
        mv.currency = self.currency
        mv.description = f"{self.get_type_display()} {self.display_number}"
        mv.reference = f"{self.display_number}"
        mv.save()   # CariMovement.save() already calls recompute_balance
        return mv

    def cancel(self, user=None, reason=""):
        """
        Cancel an issued invoice. DELETES the posted CariMovement outright
        (mirroring reverse_order_movement's semantics for orders) so the
        cari history shows no trace of the dead invoice, then recomputes
        the balance. An order-attached invoice has no movement to delete —
        it never posted one — so this is a no-op for those beyond the
        status flip.

        Cancellation is TERMINAL — there is no restore path (restore()
        below refuses), which is exactly why deleting beats posting an
        audit counter-pair here: the ledger rows would never be needed
        again and only clutter the cari statement.
        """
        if self.status == "cancelled":
            return
        if self.status == "draft":
            self.status = "cancelled"
            self.save(update_fields=["status", "updated_at"])
            return

        from django.db import transaction as _tx
        with _tx.atomic():
            # Atomic so a failure between the delete and the status flip
            # can't leave an 'issued' invoice with no ledger row (which a
            # later edit would silently re-post via resync_posted_movement).
            if self.posted_movement_id:
                mv = self.posted_movement
                cari = mv.cari
                mv.delete()   # OneToOne is SET_NULL → self.posted_movement clears
                self.posted_movement = None
                if cari:
                    cari.recompute_balance(save=True)
            self.status = "cancelled"
            self.save(update_fields=["status", "posted_movement", "updated_at"])

    def restore(self, user=None, reason=""):
        """
        Cancelled invoices are TERMINAL and can never be reopened: cancel()
        deletes the posted ledger movement (and, for order-attached ones,
        the order itself is terminally cancelled; for purchases the stock
        was hard-deleted), so there is nothing consistent to restore to.
        Kept only so any stale caller fails loudly instead of half-reviving
        an invoice.
        """
        raise ValidationError("İptal edilen fatura geri açılamaz.")


# ---------------------------------------------------------------------------
# 5. InvoiceItem — Fatura Kalemi
# ---------------------------------------------------------------------------
class InvoiceItem(models.Model):
    class Meta:
        verbose_name = _("Invoice Item")
        verbose_name_plural = _("Invoice Items")
        ordering = ["invoice", "line_no", "id"]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    line_no = models.PositiveIntegerField(default=1)

    # Optional product/variant link — items can also be free-text
    product = models.ForeignKey(
        "marketing.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice_items",
    )
    variant = models.ForeignKey(
        "marketing.ProductVariant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice_items",
    )

    # For auto-issued sales invoices (create_invoice_for_order): the
    # order line this item mirrors, so the invoice can show exactly
    # which physical tops (OrderRollReservation) fulfilled it — same
    # traceability WarehouseProductRoll.purchase_invoice_item gives
    # purchase invoices, mirrored for the sales side.
    order_item = models.ForeignKey(
        "operating.OrderItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice_items",
    )

    description = models.CharField(max_length=300)
    quantity    = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("1.000"))
    unit        = models.CharField(max_length=20, default="pcs")

    unit_price    = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"),
                                        help_text="Unit price excluding VAT")
    discount_rate = models.DecimalField(max_digits=5,  decimal_places=2, default=Decimal("0.00"),
                                        help_text="Discount %")
    tax_rate      = models.DecimalField(max_digits=5,  decimal_places=2, default=Decimal("20.00"),
                                        help_text="VAT %")

    # Computed
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total           = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"#{self.line_no} {self.description[:40]} — {self.total}"

    def compute(self):
        """Recompute the four derived amounts from inputs. Does not save.

        Rounds half UP, explicitly. Decimal's default is ROUND_HALF_EVEN
        (banker's rounding), which sends an exact half to the nearest EVEN
        cent — so 56.90 m × $2.45 = $139.405 billed as $139.40, and the
        same line at a price ending .35 would have gone up instead. Half
        cases are common here because metre quantities carry two decimals
        against a two-decimal price, and "half goes up" is the rule people
        check invoices against. The same rounding is applied to each
        amount, discount included."""
        qty   = self.quantity   or Decimal("0")
        price = self.unit_price or Decimal("0")
        sub   = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        disc_rate = (self.discount_rate or Decimal("0")) / Decimal("100")
        disc      = (sub * disc_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        net       = sub - disc
        tax_rate  = (self.tax_rate or Decimal("0")) / Decimal("100")
        tax       = (net * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self.subtotal        = sub
        self.discount_amount = disc
        self.tax_amount      = tax
        self.total           = net + tax

    def save(self, *args, **kwargs):
        self.compute()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.invoice_id:
                self.invoice.recompute_totals(save=True)


# Recompute parent on item delete too
from django.db.models.signals import post_delete
from django.dispatch import receiver as _receiver

@_receiver(post_delete, sender=InvoiceItem)
def _invoice_item_deleted(sender, instance, **kwargs):
    try:
        instance.invoice.recompute_totals(save=True)
    except Invoice.DoesNotExist:
        pass


# ---------------------------------------------------------------------------
# 6. Payment — Tahsilat / Ödeme
# ---------------------------------------------------------------------------
class Payment(models.Model):
    class Meta:
        verbose_name = _("Collection / Payment")
        verbose_name_plural = _("Collections / Payments")
        unique_together = ("book", "number")
        indexes = [
            models.Index(fields=["book", "-date"]),
            models.Index(fields=["cari", "-date"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-date", "-id"]

    PAYMENT_TYPES = [
        ("collection", _("Collection (from customer)")),
        ("payment",    _("Payment (to supplier)")),
        ("refund_in",  _("Refund to Customer")),
        ("refund_out", _("Refund from Supplier")),
    ]
    METHOD_CHOICES = [
        ("cash",            _("Cash")),
        ("bank_transfer",   _("Bank Transfer / EFT")),
        ("credit_card",     _("Credit Card (POS)")),
        ("check",           _("Check")),
        ("promissory_note", _("Promissory Note")),
        ("offset",          _("Offset")),
        ("other",           _("Other")),
    ]
    STATUS_CHOICES = [
        ("draft",     _("Draft")),
        ("confirmed", _("Confirmed")),
        ("cancelled", _("Cancelled")),
    ]

    cari = models.ForeignKey(CariAccount, on_delete=models.PROTECT, related_name="payments")
    book = models.ForeignKey("accounting.Book", on_delete=models.PROTECT, related_name="payments")

    number = models.CharField(max_length=30)
    type   = models.CharField(max_length=20, choices=PAYMENT_TYPES, default="collection")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="bank_transfer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    date          = models.DateField()
    amount        = models.DecimalField(max_digits=14, decimal_places=2,
                                        help_text="Always positive — sign comes from `type`")
    currency      = models.ForeignKey("accounting.CurrencyCategory", on_delete=models.PROTECT)
    # The rate the person recording this payment says applies, to the book's
    # base currency. Null means they did not say, and the published rate for
    # `date` is used instead.
    #
    # Nullable rather than defaulting to 1.000000, because a default is
    # indistinguishable from a deliberate entry: a payment in lira carrying
    # "1.000000" would otherwise read as an instruction to treat one lira as
    # one dollar. Null says nothing, which is what an untouched field means.
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6,
                                        null=True, blank=True,
                                        help_text="Rate to the book's base "
                                                  "currency. Blank → the "
                                                  "published rate for the date.")

    # Cash side — money lands here (or leaves here)
    cash_account = models.ForeignKey(
        "accounting.CashAccount", on_delete=models.PROTECT,
        null=True, blank=True, related_name="cari_payments",
    )

    # Posted CariMovement (set on confirm)
    posted_movement = models.OneToOneField(
        CariMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payment",
    )

    description = models.CharField(max_length=300, blank=True)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="created_payments")

    # -- helpers -----------------------------------------------------------
    @property
    def ledger_sign(self):
        """Sign applied to CariMovement.amount."""
        return -1 if self.type in ("collection", "refund_out") else +1

    @property
    def cash_sign(self):
        """Sign applied to CashAccount.balance delta."""
        return +1 if self.type in ("collection", "refund_out") else -1

    @property
    def movement_type(self):
        return {
            "collection": "collection",
            "payment":    "payment",
            "refund_in":  "payment",
            "refund_out": "collection",
        }[self.type]

    @property
    def allocated_amount(self):
        return self.allocations.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

    @property
    def unallocated_amount(self):
        return (self.amount or Decimal("0.00")) - self.allocated_amount

    def __str__(self):
        return f"{self.number} | {self.cari.name} | {self.amount} {self.currency.code}"

    def ledger_exchange_rate(self):
        """The rate this payment's ledger row converts at.

        None means nobody typed one and the published rate for the date
        applies — see CariMovement.entered_rate, which is what asks.
        """
        return self.exchange_rate

    # -- lifecycle ---------------------------------------------------------
    def confirm(self, user=None):
        """Draft → Confirmed. Posts to CariMovement and CashAccount."""
        if self.status == "confirmed":
            return
        if self.status == "cancelled":
            raise ValidationError("A cancelled payment cannot be confirmed.")
        if self.amount is None or self.amount <= 0:
            raise ValidationError("Amount must be greater than zero.")

        with transaction.atomic():
            # 1) Cari ledger entry
            movement = CariMovement.objects.create(
                cari=self.cari,
                book=self.book,
                date=self.date,
                amount=self.amount * Decimal(self.ledger_sign),
                currency=self.currency,
                movement_type=self.movement_type,
                description=f"{self.get_type_display()} — {self.number}",
                reference=self.number,
                source_type=ContentType.objects.get_for_model(Payment),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )

            # 2) Cash account balance update (raw UPDATE to bypass CashAccount.clean)
            if self.cash_account_id:
                from accounting.models import CashAccount
                delta = self.amount * Decimal(self.cash_sign)
                CashAccount.objects.filter(pk=self.cash_account_id).update(
                    balance=models.F("balance") + delta
                )

            # 3) Mark confirmed
            self.posted_movement = movement
            self.status = "confirmed"
            self.save(update_fields=["status", "posted_movement", "updated_at"])

            # 4) Record the cash movement in the cash ledger. After the
            #    balance shift above and the status flip, so the row stamps
            #    the position the payment leaves behind.
            self.sync_cash_entry()

            # 4) Re-derive paid_amount/status on every allocated invoice
            for alloc in self.allocations.select_related("invoice").all():
                if alloc.invoice_id:
                    alloc.invoice.recompute_payment(save=True)

        return movement

    def sync_cash_entry(self):
        """Make the cash ledger row match this payment's cash effect.

        A payment moves cash by writing straight to CashAccount.balance —
        confirm() does it, the edit view does it, cancel() reverses it. None
        of them used to record anything in CashTransactionEntry, so money
        moved that the transactions page never showed and its running total
        never counted. That is how book 2 came to read $59.60 against a real
        $1,804.98.

        Call this AFTER the balance has been shifted: the entry stamps the
        account balance and the book total as it finds them.

        Idempotent, and covers every direction — a payment that gains a cash
        account gets a row, one that loses it (or is cancelled, or reverts to
        draft) has its row removed, and an edited amount updates in place
        rather than leaving a second row behind.
        """
        from accounting.models import CashTransactionEntry

        content_type = ContentType.objects.get_for_model(Payment)
        existing = CashTransactionEntry.objects.filter(
            content_type=content_type, content_pk=self.pk
        ).first()

        # Only a confirmed payment against a cash account moves cash.
        if self.status != "confirmed" or not self.cash_account_id:
            if existing:
                existing.delete()
            return None

        entry = existing or CashTransactionEntry(
            content_type=content_type, content_pk=self.pk
        )
        entry.book = self.book
        entry.amount = self.amount
        entry.is_amount_positive = self.cash_sign > 0
        entry.currency = self.currency
        entry.cash_account_id = self.cash_account_id
        entry.date = self.date
        # Reconverted on purpose: the amount, the currency or the rate may
        # have just changed, so what the row is worth in base currency has
        # to be worked out again rather than carried over. Blanking the rate
        # too lets a newly entered one take effect — resolve_exchange_rate
        # would otherwise keep the rate already on the row, which is the
        # right answer everywhere except here.
        entry.amount_in_base_currency = None
        entry.exchange_rate = None
        entry.save()
        return entry

    def resync_posted_movement(self, user=None):
        """Refresh the ledger row after an edit to an already-confirmed payment.

        The SAME CariMovement is updated in place — never delete+recreate,
        because `posted_movement` and the statement both reference it by
        id. Draft payments have posted nothing yet and cancelled ones are
        terminal, so both are no-ops.

        If `posted_movement` is somehow missing on a confirmed payment
        (confirm() always sets it in the same transaction, so this should
        not happen), post a fresh one rather than silently leaving the
        cari balance stale.
        """
        if self.status != "confirmed":
            return None

        amount = self.amount * Decimal(self.ledger_sign)
        description = f"{self.get_type_display()} — {self.number}"

        mv = self.posted_movement
        if mv is None:
            mv = CariMovement.objects.create(
                cari=self.cari,
                book=self.book,
                date=self.date,
                amount=amount,
                currency=self.currency,
                movement_type=self.movement_type,
                description=description,
                reference=self.number,
                source_type=ContentType.objects.get_for_model(Payment),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )
            self.posted_movement = mv
            self.save(update_fields=["posted_movement", "updated_at"])
            return mv

        mv.amount = amount
        mv.amount_base = Decimal("0")   # force recompute on save
        mv.date = self.date
        mv.currency = self.currency
        mv.movement_type = self.movement_type
        mv.description = description
        mv.reference = self.number
        mv.save()   # CariMovement.save() already calls recompute_balance
        return mv

    def cancel(self, user=None, reason=""):
        """Cancel a confirmed payment. Removes the CariMovement, reverses
        cash, and re-derives the invoice allocations.

        The posted movement is DELETED rather than reversed with a
        counter-row, matching Invoice.cancel(): cancellation is terminal
        (no restore path exists for either), so the pair would never be
        needed again and only made every cancelled payment read as two
        lines on the statement. The audit trail lives on the Payment,
        which keeps its number, dates and status=cancelled.
        """
        if self.status == "cancelled":
            return
        if self.status == "draft":
            self.status = "cancelled"
            self.save(update_fields=["status", "updated_at"])
            return

        with transaction.atomic():
            # 1) Drop the cari ledger row
            if self.posted_movement_id:
                mv = self.posted_movement
                cari = mv.cari
                mv.delete()   # OneToOne is SET_NULL → posted_movement clears
                self.posted_movement = None
                if cari:
                    cari.recompute_balance(save=True)

            # 2) Reverse cash
            if self.cash_account_id:
                from accounting.models import CashAccount
                delta = self.amount * Decimal(self.cash_sign)
                CashAccount.objects.filter(pk=self.cash_account_id).update(
                    balance=models.F("balance") - delta
                )

            # 3) Flip status (allocations now no longer count, because Invoice.recompute_payment
            #    filters by payment.status == 'confirmed')
            self.status = "cancelled"
            self.save(update_fields=["status", "posted_movement", "updated_at"])

            # The cash went back, so the cash ledger row goes with it —
            # sync_cash_entry drops it now that the status is cancelled.
            self.sync_cash_entry()

            # 4) Re-derive invoices
            for alloc in self.allocations.select_related("invoice").all():
                if alloc.invoice_id:
                    alloc.invoice.recompute_payment(save=True)


# ---------------------------------------------------------------------------
# 7. PaymentAllocation — Ödeme ↔ Fatura eşleştirmesi
# ---------------------------------------------------------------------------
class PaymentAllocation(models.Model):
    class Meta:
        verbose_name = _("Payment Allocation")
        verbose_name_plural = _("Payment Allocations")
        indexes = [models.Index(fields=["invoice"]), models.Index(fields=["payment"])]
        ordering = ["payment", "id"]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, null=True, blank=True,
        related_name="allocations",
        help_text="Leave empty to keep as account advance.",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2,
                                 help_text="Always positive — the portion of the payment applied here.")

    def __str__(self):
        target = self.invoice.number if self.invoice_id else "ADVANCE"
        return f"{self.payment.number} → {target} : {self.amount}"

    def clean(self):
        super().clean()
        if self.amount is None or self.amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if self.invoice_id and self.invoice.cari_id != self.payment.cari_id:
            raise ValidationError({"invoice": "Invoice's account must be the same as the payment's account."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.invoice_id and self.payment.status == "confirmed":
                self.invoice.recompute_payment(save=True)


@_receiver(post_delete, sender=PaymentAllocation)
def _alloc_deleted(sender, instance, **kwargs):
    if instance.invoice_id:
        try:
            instance.invoice.recompute_payment(save=True)
        except Invoice.DoesNotExist:
            pass


# ---------------------------------------------------------------------------
# 8. CheckOrPromissoryNote — Çek / Senet
# ---------------------------------------------------------------------------
class CheckOrPromissoryNote(models.Model):
    class Meta:
        verbose_name = _("Check / Promissory Note")
        verbose_name_plural = _("Checks / Promissory Notes")
        indexes = [
            models.Index(fields=["book", "status"]),
            models.Index(fields=["cari", "-due_date"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["-due_date", "-id"]

    INSTRUMENT_TYPES = [
        ("check",            _("Check")),
        ("promissory_note",  _("Promissory Note")),
    ]
    DIRECTION_CHOICES = [
        ("received", _("Received from Customer")),
        ("given",    _("Given to Supplier")),
    ]
    STATUS_CHOICES = [
        ("portfolio", _("In Portfolio")),
        ("endorsed",  _("Endorsed")),
        ("deposited", _("Deposited to Bank")),
        ("cleared",   _("Cleared")),
        ("bounced",   _("Bounced")),
        ("returned",  _("Returned")),
        ("cancelled", _("Cancelled")),
    ]

    book = models.ForeignKey("accounting.Book", on_delete=models.PROTECT, related_name="checks")
    cari = models.ForeignKey(CariAccount, on_delete=models.PROTECT, related_name="checks",
                             help_text="Account that gave or received the instrument")

    instrument = models.CharField(max_length=20, choices=INSTRUMENT_TYPES, default="check")
    direction  = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="received")
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default="portfolio")

    serial_no = models.CharField(max_length=50)
    bank      = models.CharField(max_length=100, blank=True, help_text="Bank name (for check)")
    branch    = models.CharField(max_length=100, blank=True, help_text="Branch (for check)")
    account_no= models.CharField(max_length=50,  blank=True)
    drawer    = models.CharField(max_length=200, blank=True, help_text="Drawer name")

    amount   = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey("accounting.CurrencyCategory", on_delete=models.PROTECT)

    issue_date = models.DateField()
    due_date   = models.DateField()

    # When endorsed to another cari
    endorsed_to = models.ForeignKey(
        CariAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name="endorsed_checks",
    )

    # Cari ledger row that recorded the original transfer (receive/give)
    posted_movement = models.OneToOneField(
        CariMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="check_initial",
    )
    # Cari ledger row that recorded the endorsement (received → endorsed)
    endorse_movement = models.OneToOneField(
        CariMovement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="check_endorsement",
    )
    # CashAccount that received/lost money on clear
    cleared_cash_account = models.ForeignKey(
        "accounting.CashAccount", on_delete=models.PROTECT, null=True, blank=True,
        related_name="cleared_checks",
    )

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_checks")

    def __str__(self):
        return f"{self.get_instrument_display()} #{self.serial_no} | {self.amount} {self.currency.code} | {self.cari.name}"

    # ---- lifecycle: initial post --------------------------------------
    def _post_initial_movement(self, user=None):
        """
        Post the first CariMovement when the instrument enters the portfolio.
        - received: amount = -X on cari (their balance shrinks, like a collection)
        - given   : amount = +X on cari (their balance moves toward zero, like a payment)
        """
        sign = -1 if self.direction == "received" else +1
        mv = CariMovement.objects.create(
            cari=self.cari,
            book=self.book,
            date=self.issue_date,
            due_date=self.due_date,
            amount=self.amount * Decimal(sign),
            currency=self.currency,
            movement_type="check_in" if self.direction == "received" else "check_out",
            description=f"{self.get_instrument_display()} — {self.get_direction_display()} #{self.serial_no}",
            reference=self.serial_no,
            source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
            source_id=self.pk,
            created_by=user.member if user and hasattr(user, "member") else None,
        )
        self.posted_movement = mv
        self.save(update_fields=["posted_movement", "updated_at"])
        return mv

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.posted_movement_id is None:
            self._post_initial_movement()

    # ---- state transitions --------------------------------------------
    def endorse(self, to_cari, user=None):
        """Hand a received check over to another account (typically a supplier)."""
        if self.direction != "received":
            raise ValidationError("Only received checks/notes can be endorsed.")
        if self.status != "portfolio":
            raise ValidationError(f"Cannot endorse from status: {self.status}")
        if to_cari.book_id != self.book_id:
            raise ValidationError("Endorsed account must be in the same book.")

        with transaction.atomic():
            # New CariMovement: +X on the endorsed-to cari (we 'paid' them with the check)
            mv = CariMovement.objects.create(
                cari=to_cari,
                book=self.book,
                date=timezone.now().date(),
                due_date=self.due_date,
                amount=self.amount,
                currency=self.currency,
                movement_type="check_out",
                description=f"Endorsement — {self.get_instrument_display()} #{self.serial_no} (source: {self.cari.code})",
                reference=f"ENDORSE {self.serial_no}",
                source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )
            self.endorsed_to = to_cari
            self.endorse_movement = mv
            self.status = "endorsed"
            self.save(update_fields=["endorsed_to", "endorse_movement", "status", "updated_at"])
        return mv

    def deposit(self, user=None):
        """Mark a received check as deposited to bank (awaiting clearance)."""
        if self.direction != "received":
            raise ValidationError("Only received checks can be deposited.")
        if self.status != "portfolio":
            raise ValidationError(f"Cannot deposit from status: {self.status}")
        self.status = "deposited"
        self.save(update_fields=["status", "updated_at"])

    def clear(self, cash_account=None, user=None):
        """
        Mark the instrument as cleared.
        - received: money lands in cash_account (cash += amount).
        - given   : money leaves cash_account (cash -= amount).
        """
        if self.status not in ("portfolio", "deposited"):
            raise ValidationError(f"Cannot clear (current status: {self.status})")
        if not cash_account:
            raise ValidationError("Cash account is required.")
        if cash_account.book_id != self.book_id:
            raise ValidationError("Cash account must be in the same book.")

        from accounting.models import CashAccount
        with transaction.atomic():
            delta = self.amount if self.direction == "received" else -self.amount
            CashAccount.objects.filter(pk=cash_account.pk).update(
                balance=models.F("balance") + delta
            )
            self.cleared_cash_account = cash_account
            self.status = "cleared"
            self.save(update_fields=["cleared_cash_account", "status", "updated_at"])

    def bounce(self, user=None, reason=""):
        """
        Received check came back unpaid.
        Reverse the original cari posting (+X back to drawer).
        If it was already deposited or endorsed, we still reverse the drawer
        side — operator decides downstream how to chase the funds.
        """
        if self.direction != "received":
            raise ValidationError("Only received checks can bounce.")
        if self.status in ("bounced", "cancelled"):
            return
        with transaction.atomic():
            CariMovement.objects.create(
                cari=self.cari,
                book=self.book,
                date=timezone.now().date(),
                amount=self.amount,  # +X — drawer owes us again
                currency=self.currency,
                movement_type="adjustment",
                description=f"BOUNCED — {self.get_instrument_display()} #{self.serial_no}"
                            + (f" ({reason})" if reason else ""),
                reference=f"BOUNCE {self.serial_no}",
                source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )
            self.status = "bounced"
            self.save(update_fields=["status", "updated_at"])

    def cancel(self, user=None, reason=""):
        """Cancel the instrument and remove every ledger row it posted.

        The rows are DELETED rather than reversed with counter-movements,
        matching Payment.cancel() and Invoice.cancel(): cancellation is
        terminal for all three (none has a restore path), so a
        counter-pair would never be needed again and only made a
        cancelled instrument read as two lines on the statement.

        Three rows can be involved — the initial receipt/hand-over, an
        endorsement onto another account, and a bounce. The bounce goes
        too: cancelling the instrument undoes both the receipt and the
        come-back, which leaves each account exactly where it stood
        before the check was entered. `reason` is no longer recorded on
        the ledger (there is no row to carry it) — the instrument's own
        status and notes are where that belongs.
        """
        if self.status == "cancelled":
            return
        with transaction.atomic():
            touched = []

            # Initial movement (this cari) and the endorsement (the cari
            # it was handed to). Both are OneToOne SET_NULL, so deleting
            # the row clears the FK — assign None as well so the instance
            # in hand matches what was just saved.
            for field in ("posted_movement", "endorse_movement"):
                mv = getattr(self, field)
                if mv is None:
                    continue
                touched.append(mv.cari)
                mv.delete()
                setattr(self, field, None)

            # The BOUNCED counter-row, if this one came back unpaid.
            bounced = CariMovement.objects.filter(
                source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
                source_id=self.pk,
                reference__startswith="BOUNCE",
            )
            touched.extend(mv.cari for mv in bounced)
            bounced.delete()

            # De-duplicate by pk: the same account can own more than one
            # of the rows above, and recomputing it twice is wasted work.
            for cari in {c.pk: c for c in touched if c}.values():
                cari.recompute_balance(save=True)

            self.status = "cancelled"
            self.save(update_fields=["status", "posted_movement",
                                     "endorse_movement", "updated_at"])



# ---------------------------------------------------------------------------
# CariTransfer — move a balance from one current account to another
# ---------------------------------------------------------------------------
class CariTransfer(models.Model):
    """A virman: the debt moves, the money does not.

    Transferring X from A to B posts -X on A and +X on B, so whatever A
    owed us is now owed by B and the book's total receivable is
    unchanged. Nothing touches a CashAccount — no cash has moved, only
    the question of who owes it.

    Both legs are posted in ONE currency on ONE date, which is what makes
    them cancel: CariMovement derives its base-currency amount from the
    rate of its own date, so a pair sharing both fields converts at the
    same rate and nets to zero in USD as well as in the currency typed.
    Posting each leg in its own account's default currency would leave a
    silent FX residue on the book.

    The two movements are kept on the transfer so `unpost()` can take
    back exactly the rows it wrote rather than guessing from a
    description.
    """

    class Meta:
        verbose_name = _("Account Transfer")
        verbose_name_plural = _("Account Transfers")
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["book", "-date"]),
        ]

    book = models.ForeignKey("accounting.Book", on_delete=models.CASCADE,
                             related_name="cari_transfers")
    date = models.DateField()

    from_cari = models.ForeignKey(CariAccount, on_delete=models.PROTECT,
                                  related_name="transfers_out")
    to_cari   = models.ForeignKey(CariAccount, on_delete=models.PROTECT,
                                  related_name="transfers_in")

    amount   = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey("accounting.CurrencyCategory",
                                 on_delete=models.PROTECT,
                                 related_name="cari_transfers")

    # The rate the person recording this transfer says applies, to the
    # book's base currency. Null means they did not say, and the published
    # rate for `date` is used instead.
    #
    # Nullable rather than defaulting to 1.000000, for the same reason
    # Payment.exchange_rate is: a default cannot be told apart from a
    # deliberate entry, so a transfer in lira carrying "1.000000" would
    # read as an instruction to treat one lira as one dollar. Null says
    # nothing, which is what an untouched field means.
    # 8 decimals for the reason CariMovement.exchange_rate gives — and it
    # has to match that column, since post() stamps this straight onto both
    # legs. Widening one without the other would round the rate right back
    # on the way into the ledger.
    exchange_rate = models.DecimalField(max_digits=16, decimal_places=8,
                                        null=True, blank=True,
                                        help_text="Rate to the book's base "
                                                  "currency. Blank → the "
                                                  "published rate for the date.")

    description = models.CharField(max_length=300, blank=True)

    # The rows this transfer wrote — set by post(), cleared by unpost().
    from_movement = models.OneToOneField(CariMovement, on_delete=models.SET_NULL,
                                         null=True, blank=True,
                                         related_name="transfer_from")
    to_movement   = models.OneToOneField(CariMovement, on_delete=models.SET_NULL,
                                         null=True, blank=True,
                                         related_name="transfer_to")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name="created_cari_transfers")

    def __str__(self):
        return (f"{self.from_cari.code} → {self.to_cari.code} | "
                f"{self.amount} {self.currency.code}")

    def clean(self):
        super().clean()
        if self.from_cari_id and self.from_cari_id == self.to_cari_id:
            raise ValidationError(
                _("Pick two different accounts — a transfer to itself moves nothing.")
            )
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": _("Amount must be greater than zero.")})
        # Zero would convert the whole transfer to nothing; negative would
        # flip which side of the book each leg lands on.
        if self.exchange_rate is not None and self.exchange_rate <= 0:
            raise ValidationError({
                "exchange_rate": _("Exchange rate must be greater than zero.")
            })
        # The page is per-book and the balances are per-book, so a transfer
        # spanning two books would silently move a balance out of one set of
        # books and into another.
        if self.book_id:
            for field in ("from_cari", "to_cari"):
                cari = getattr(self, field, None)
                if cari and cari.book_id != self.book_id:
                    raise ValidationError({
                        field: _("This account belongs to another book.")
                    })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @transaction.atomic
    def post(self, user=None):
        """Write the two ledger rows. Idempotent — a second call is a no-op."""
        if self.from_movement_id and self.to_movement_id:
            return

        member = getattr(user, "member", None) if user else self.created_by
        source_type = ContentType.objects.get_for_model(CariTransfer)
        label = self.description or _("Account transfer")
        rate = self.resolved_rate()

        def leg(cari, signed, other):
            mv = CariMovement(
                cari=cari,
                book=self.book,
                date=self.date,
                amount=signed,
                currency=self.currency,
                movement_type="adjustment",
                description=f"{label} — {other.code} {other.name}",
                reference=f"TRANSFER {self.pk}",
                source_type=source_type,
                source_id=self.pk,
                created_by=member,
            )
            # Both legs are stamped from ONE rate, resolved once above,
            # rather than each fetching its own. Same currency and same
            # date would normally get the same answer, but "normally" is
            # not good enough here: if the two lookups ever disagreed —
            # a cache expiring between them, a rate source flapping — the
            # pair would stop cancelling and leave a residue on the book
            # that nobody entered.
            mv.exchange_rate = rate
            mv.amount_base = (signed * rate).quantize(Decimal("0.01"))
            mv.save()
            return mv

        # The debt moves: the source owes us less, the destination more.
        self.from_movement = leg(self.from_cari, -self.amount, self.to_cari)
        self.to_movement   = leg(self.to_cari,    self.amount, self.from_cari)
        # update_fields, so full_clean() in save() is not re-run on rows the
        # form has already validated.
        super().save(update_fields=["from_movement", "to_movement"])

    def ledger_exchange_rate(self):
        """The rate this transfer's legs convert at, for any path that
        recomputes one. post() stamps both legs directly, so this is a
        floor rather than the normal route — but a leg recomputed without
        it would fall back to the published rate and stop cancelling
        against its pair.
        """
        return self.exchange_rate

    def resolved_rate(self):
        """The rate these legs convert at: the one typed, or the published
        rate for the date when nobody typed one.

        Falls back to 1.0 only when the lookup itself comes back empty,
        which is what CariMovement.save() does on its own — a transfer
        should not be blocked because a rate source is unreachable.
        """
        base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
        if self.currency.code == base_code:
            return Decimal("1.000000")
        if self.exchange_rate:
            return Decimal(str(self.exchange_rate))
        from accounting.services import get_exchange_rate
        rate = get_exchange_rate(
            self.currency.code, base_code, on_date=self.date
        ) or Decimal("1.000000")
        return Decimal(str(rate))

    @transaction.atomic
    @transaction.atomic
    def repost(self, user=None):
        """Rewrite the two ledger rows this transfer already has, in place.

        Correcting a transfer used to be unpost() then post() — delete both
        rows, write two new ones. Arithmetically identical, and it renumbered
        the ledger every time: a leg linked to as movement #1158 came back as
        #1169, so every link into it died on a save that changed nothing but
        the amount. Ledger rows are cited, from an invoice, a note, a
        colleague's message; an id that moves under them is an id nobody can
        use.

        So the rows keep their identity and their fields are rewritten. The
        invariant post() exists to protect is unchanged and for the same
        reason: ONE rate resolved once here, stamped on both legs together
        with one date, so the pair still converts at the same rate and nets
        to zero in base currency as well as in the currency typed.

        Rewriting rather than deleting is also why the accounts a leg moved
        AWAY from have to be recomputed by name. CariMovement.save() refreshes
        the account the row belongs to NOW; the one it just left keeps a
        cached balance still counting a row that is no longer there.

        An unposted transfer has nothing to rewrite, so it is simply posted.
        """
        if not (self.from_movement_id and self.to_movement_id):
            self.post(user=user)
            return

        label = self.description or _("Account transfer")
        rate = self.resolved_rate()
        touched = []

        def leg(mv, cari, signed, other):
            # Where the row was, before it is pointed anywhere else.
            touched.append(mv.cari)
            mv.cari = cari
            mv.book = self.book
            mv.date = self.date
            mv.amount = signed
            mv.currency = self.currency
            mv.description = f"{label} — {other.code} {other.name}"
            mv.reference = f"TRANSFER {self.pk}"
            # Stamped, not left to CariMovement.save() to derive: it only
            # fills amount_base when falsy and would otherwise re-look-up a
            # rate per leg, which is the pair drifting apart — see post().
            mv.exchange_rate = rate
            mv.amount_base = (signed * rate).quantize(Decimal("0.01"))
            mv.save()
            touched.append(cari)

        # created_by is left alone on purpose: whoever entered the row still
        # entered it. A correction is not a re-entry.
        leg(self.from_movement, self.from_cari, -self.amount, self.to_cari)
        leg(self.to_movement, self.to_cari, self.amount, self.from_cari)

        for cari in {c.pk: c for c in touched if c}.values():
            cari.recompute_balance(save=True)

    def unpost(self):
        """Delete both legs and re-derive the two balances.

        Deleted rather than reversed with counter-movements, matching
        Payment.cancel() and CheckOrPromissoryNote.cancel(): an undone
        transfer should leave both statements as if it never happened,
        not as two lines that cancel.
        """
        touched = [self.from_cari, self.to_cari]
        for field in ("from_movement", "to_movement"):
            mv = getattr(self, field)
            if mv:
                mv.delete()
                setattr(self, field, None)
        super().save(update_fields=["from_movement", "to_movement"])
        for cari in {c.pk: c for c in touched if c}.values():
            cari.recompute_balance(save=True)
