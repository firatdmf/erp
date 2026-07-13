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
      CariMovement (which in turn mirrors to legacy AR/AP via signals).
    - Cancelling a posted invoice creates a counter-CariMovement (audit-safe).

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

Sync with legacy accounting (signals.py):
    A CariMovement automatically mirrors itself into
    accounting.AssetAccountsReceivable (when amount > 0)
    or LiabilityAccountsPayable (when amount < 0)
    so existing dashboards keep working.
"""
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounting.models import Book, CurrencyCategory
from authentication.models import Member
from crm.models import Company, Contact, Supplier


# ---------------------------------------------------------------------------
# 1. CariAccount — the unified customer/supplier card
# ---------------------------------------------------------------------------
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

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="cari_accounts")

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
        CurrencyCategory,
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

    # Cached aggregates — kept in sync by CariMovement signals
    cached_balance      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    cached_balance_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    last_movement_at    = models.DateTimeField(null=True, blank=True)

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
        """Recalculate cached_balance from movements. Safe to call any time."""
        agg = self.movements.aggregate(
            total=Sum("amount"),
            total_base=Sum("amount_base"),
            last=models.Max("created_at"),
        )
        self.cached_balance      = (agg["total"]      or Decimal("0.00"))
        self.cached_balance_base = (agg["total_base"] or Decimal("0.00"))
        self.last_movement_at    = agg["last"]
        if save:
            CariAccount.objects.filter(pk=self.pk).update(
                cached_balance=self.cached_balance,
                cached_balance_base=self.cached_balance_base,
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
        return self.default_currency.symbol or self.default_currency.code


# ---------------------------------------------------------------------------
# 2. CariMovement — the atomic ledger row
# ---------------------------------------------------------------------------
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
        ("legacy_ar",        _("Legacy - Receivable")),
        ("legacy_ap",        _("Legacy - Payable")),
    ]

    cari     = models.ForeignKey(CariAccount, on_delete=models.CASCADE, related_name="movements")
    book     = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="cari_movements")
    date     = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    amount        = models.DecimalField(max_digits=14, decimal_places=2)
    currency      = models.ForeignKey(CurrencyCategory, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("1.000000"),
                                        help_text="Rate from movement currency to base (USD)")
    amount_base   = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"),
                                        help_text="Amount normalized to base currency (USD)")

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)

    source_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    source_id   = models.PositiveIntegerField(null=True, blank=True)
    source      = GenericForeignKey("source_type", "source_id")

    description = models.CharField(max_length=300, blank=True)
    reference   = models.CharField(max_length=50,  blank=True, help_text="Invoice no, check no, etc.")

    # Back-reference to the legacy accounting row this movement mirrors into.
    # Populated by signals.py so updates/deletes stay in lock-step.
    legacy_ar_id = models.PositiveIntegerField(null=True, blank=True)
    legacy_ap_id = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_cari_movements")

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.cari.code} | {self.date} | {sign}{self.amount} {self.currency.code}"

    def save(self, *args, **kwargs):
        base_code = getattr(settings, "BASE_CURRENCY_CODE", "USD")
        if self.currency.code == base_code:
            self.exchange_rate = Decimal("1.000000")
            self.amount_base = self.amount.quantize(Decimal("0.01"))
        elif not self.amount_base:
            from accounting.services import get_exchange_rate
            rate = get_exchange_rate(self.currency.code, base_code) or Decimal("1.000000")
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

    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="cari_settings")

    next_cari_seq    = models.PositiveIntegerField(default=1)
    next_invoice_seq = models.PositiveIntegerField(default=1)
    next_payment_seq = models.PositiveIntegerField(default=1)

    cari_code_prefix  = models.CharField(max_length=10, default="CARI")
    cari_code_padding = models.PositiveSmallIntegerField(default=3)

    default_tax_rate          = models.DecimalField(max_digits=5, decimal_places=2,
                                                    default=Decimal("20.00"))
    default_payment_term_days = models.PositiveIntegerField(default=30)
    default_currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="cari_settings_default",
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
    book   = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="invoices")

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

    currency      = models.ForeignKey(CurrencyCategory, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6,
                                        default=Decimal("1.000000"))

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
    # Cancellation creates a counter-movement and clears this pointer.
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
        return f"{self.series}-{self.number} | {self.cari.name} | {self.total} {self.currency.code}"

    # -- helpers -----------------------------------------------------------
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

        # Order-attached invoice → info-only (amount=0); standalone → real posting.
        if self.order_id:
            amount_signed = Decimal("0.00")
        else:
            amount_signed = self.total * Decimal(self.ledger_sign)

        movement = CariMovement.objects.create(
            cari=self.cari,
            book=self.book,
            date=self.date,
            due_date=self.due_date,
            amount=amount_signed,
            currency=self.currency,
            movement_type=self.movement_type,
            description=f"{self.get_type_display()} {self.series}-{self.number}",
            reference=f"{self.series}-{self.number}",
            source_type=ContentType.objects.get_for_model(Invoice),
            source_id=self.pk,
            created_by=user.member if user and hasattr(user, "member") else None,
        )
        self.posted_movement = movement
        self.status = "issued"
        self.save(update_fields=["status", "posted_movement", "updated_at"])
        return movement

    def cancel(self, user=None, reason=""):
        """
        Cancel an issued invoice. Posts a counter-movement so the
        ledger balances. Amount of the counter matches the original
        (zero for order-attached invoices, ±total for standalone),
        which means cancelling an info-only invoice movement is also
        a no-op on the balance — exactly what we want.
        Audit-safe — never deletes the original.
        """
        if self.status == "cancelled":
            return
        if self.status == "draft":
            self.status = "cancelled"
            self.save(update_fields=["status", "updated_at"])
            return

        if self.posted_movement_id:
            CariMovement.objects.create(
                cari=self.cari,
                book=self.book,
                date=self.date,
                amount=-self.posted_movement.amount,
                currency=self.currency,
                movement_type="adjustment",
                description=f"CANCEL — {self.get_type_display()} {self.series}-{self.number}"
                            + (f" ({reason})" if reason else ""),
                reference=f"CANCEL {self.series}-{self.number}",
                source_type=ContentType.objects.get_for_model(Invoice),
                source_id=self.pk,
                created_by=user.member if user and hasattr(user, "member") else None,
            )
        self.status = "cancelled"
        self.save(update_fields=["status", "updated_at"])

    def restore(self, user=None, reason=""):
        """
        Restore a cancelled invoice. Inverse of cancel(): posts a
        counter-movement to the cancel-counter (re-establishing the
        original posting) and puts status back into an active state.
        Audit-safe — never deletes the cancel-counter movement.
        """
        if self.status != "cancelled":
            raise ValidationError(f"Only cancelled invoices can be restored (current status: {self.status}).")

        if not self.posted_movement_id:
            self.status = "draft"
            self.save(update_fields=["status", "updated_at"])
            return

        CariMovement.objects.create(
            cari=self.cari,
            book=self.book,
            date=self.date,
            amount=self.posted_movement.amount,
            currency=self.currency,
            movement_type="adjustment",
            description=f"RESTORE — {self.get_type_display()} {self.series}-{self.number}"
                        + (f" ({reason})" if reason else ""),
            reference=f"RESTORE {self.series}-{self.number}",
            source_type=ContentType.objects.get_for_model(Invoice),
            source_id=self.pk,
            created_by=user.member if user and hasattr(user, "member") else None,
        )
        self.status = "issued"
        self.save(update_fields=["status", "updated_at"])
        self.recompute_payment()


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
        """Recompute the four derived amounts from inputs. Does not save."""
        qty   = self.quantity   or Decimal("0")
        price = self.unit_price or Decimal("0")
        sub   = (qty * price).quantize(Decimal("0.01"))

        disc_rate = (self.discount_rate or Decimal("0")) / Decimal("100")
        disc      = (sub * disc_rate).quantize(Decimal("0.01"))

        net       = sub - disc
        tax_rate  = (self.tax_rate or Decimal("0")) / Decimal("100")
        tax       = (net * tax_rate).quantize(Decimal("0.01"))

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
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="payments")

    number = models.CharField(max_length=30)
    type   = models.CharField(max_length=20, choices=PAYMENT_TYPES, default="collection")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="bank_transfer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    date          = models.DateField()
    amount        = models.DecimalField(max_digits=14, decimal_places=2,
                                        help_text="Always positive — sign comes from `type`")
    currency      = models.ForeignKey(CurrencyCategory, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6,
                                        default=Decimal("1.000000"))

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

            # 4) Re-derive paid_amount/status on every allocated invoice
            for alloc in self.allocations.select_related("invoice").all():
                if alloc.invoice_id:
                    alloc.invoice.recompute_payment(save=True)

        return movement

    def cancel(self, user=None, reason=""):
        """Cancel a confirmed payment. Reverses CariMovement, cash, and invoice allocations."""
        if self.status == "cancelled":
            return
        if self.status == "draft":
            self.status = "cancelled"
            self.save(update_fields=["status", "updated_at"])
            return

        with transaction.atomic():
            # 1) Counter cari movement
            if self.posted_movement_id:
                CariMovement.objects.create(
                    cari=self.cari,
                    book=self.book,
                    date=self.date,
                    amount=-self.posted_movement.amount,
                    currency=self.currency,
                    movement_type="adjustment",
                    description=f"CANCEL — {self.get_type_display()} {self.number}"
                                + (f" ({reason})" if reason else ""),
                    reference=f"CANCEL {self.number}",
                    source_type=ContentType.objects.get_for_model(Payment),
                    source_id=self.pk,
                    created_by=user.member if user and hasattr(user, "member") else None,
                )

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
            self.save(update_fields=["status", "updated_at"])

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

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="checks")
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
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.PROTECT)

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
        """Cancel the instrument and reverse the initial cari movement."""
        if self.status == "cancelled":
            return
        with transaction.atomic():
            if self.posted_movement_id:
                CariMovement.objects.create(
                    cari=self.cari,
                    book=self.book,
                    date=timezone.now().date(),
                    amount=-self.posted_movement.amount,
                    currency=self.currency,
                    movement_type="adjustment",
                    description=f"CANCEL — {self.get_instrument_display()} #{self.serial_no}"
                                + (f" ({reason})" if reason else ""),
                    reference=f"CANCEL {self.serial_no}",
                    source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
                    source_id=self.pk,
                    created_by=user.member if user and hasattr(user, "member") else None,
                )
            # If endorsed, reverse that too
            if self.endorse_movement_id and self.endorsed_to_id:
                CariMovement.objects.create(
                    cari=self.endorsed_to,
                    book=self.book,
                    date=timezone.now().date(),
                    amount=-self.endorse_movement.amount,
                    currency=self.currency,
                    movement_type="adjustment",
                    description=f"CANCEL Endorsement — {self.get_instrument_display()} #{self.serial_no}",
                    reference=f"CANCEL ENDORSE {self.serial_no}",
                    source_type=ContentType.objects.get_for_model(CheckOrPromissoryNote),
                    source_id=self.pk,
                    created_by=user.member if user and hasattr(user, "member") else None,
                )
            self.status = "cancelled"
            self.save(update_fields=["status", "updated_at"])


