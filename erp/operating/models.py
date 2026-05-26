import traceback
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from crm.models import Contact, Company

# from accounting.models import (
#     AssetInventoryRawMaterial,
#     # RawMaterialGoodsReceipt,
#     Book,
#     # RawMaterialGoodsReceiptItem,
# )
from marketing.models import Product, ProductVariant, Supplier
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# from accounting.models import AssetInventoryRawMaterial
# uuid is used to generate unique identifiers for models.
import uuid

# below is to assign api_keys to machines
import secrets


class WorkInProgressGood(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateField(blank=True, null=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="wip_goods"
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="wip_goods",
    )
    order = models.ForeignKey(
        "Order", on_delete=models.CASCADE, related_name="wip_goods"
    )


# Raw material
class RawMaterialGood(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)

    raw_type = models.CharField(
        choices=[("direct", "Direct"), ("indirect", "Indirect")],
        default=("direct"),
    )

    name = models.CharField(null=False, blank=False)
    # later add image
    # image = models.ImageField(
    #     upload_to="raw_materials/",  # folder inside MEDIA_ROOT
    #     null=True,
    #     blank=True,
    # )

    supplier_sku = models.CharField(null=True, blank=True)
    sku = models.CharField(null=False, blank=False)
    unit_of_measurement = models.CharField(
        choices=[
            ("units", "Unit"),
            ("mt", "Meter"),
            ("kg", "Kilogram"),
            ("l", "Liter"),
            ("bx", "Box"),
        ],
        null=True,
        blank=True,
        default=("units"),
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # If the user does not enter a sku, make the sku equal to the id of the object created.
    # preopulate it with the next available sku
    def save(self, *args, **kwargs):
        is_new_instance = self.pk is None
        super().save(*args, **kwargs)  # Save first to get an ID
        if is_new_instance and not self.sku:
            self.sku = str(self.pk)
            super().save(update_fields=["sku"])  # Save again with sku set

    def __str__(self):
        return (
            f"{self.name} | {(self.sku) if self.sku != self.pk else self.supplier_sku}"
        )

    @property
    def unit_cost(self):
        # Fetch the latest cost from receipts
        latest_item = self.items.select_related('receipt').order_by('-receipt__date', '-id').first()
        return latest_item.unit_cost if latest_item else 0


# when we save this model, we create an libability accounts payable
class RawMaterialGoodReceipt(models.Model):
    from accounting.models import Book, CurrencyCategory

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "receipt_number"],
                name="unique_supplier_receipt_number",
            )
        ]

    # should be approved by accounting, and operating supervisor for quality.
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, null=True, blank=True
    )
    date = models.DateField(blank=True, null=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.RESTRICT, null=False, blank=False
    )
    receipt_number = models.CharField(blank=True, null=True, max_length=50)
    invoice_number = models.CharField(blank=True, null=True, max_length=50)
    # approved = models.BooleanField(default=False)

    # commented out because currencies might change
    @property
    def amount(self):
        return sum(item.quantity * item.unit_cost for item in self.items.all())

    def __str__(self):
        return f"{self.book} | on: {self.date} From: {self.supplier} with Receipt #: {self.receipt_number}"


class RawMaterialGoodItem(models.Model):

    # asset_inventory_raw_material = models.ForeignKey(AssetInventoryRawMaterial, on_delete=models.CASCADE, related_name="items")

    raw_material_good = models.ForeignKey(
        RawMaterialGood,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="items",
    )
    receipt = models.ForeignKey(
        RawMaterialGoodReceipt,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="items",
    )

    # this should be invisible field to the staff.
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )

    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=False
    )

    def __str__(self):
        currency_symbol = self.receipt.currency.symbol if self.receipt.currency else ""
        return f"{self.raw_material_good.name} from {self.receipt.supplier} | {self.quantity}@{currency_symbol}{self.unit_cost}"

    def save(self, *args, **kwargs):

        self.full_clean()
        # try:
        #     # asset_inventory_raw_material = get_object_or_404(AssetInventoryRawMaterial, sku=self.raw_material_good.sku)
        #     asset_inventory_raw_material = AssetInventoryRawMaterial.objects.get(
        #         sku=self.raw_material_good.sku
        #     )
        # except AssetInventoryRawMaterial.DoesNotExist:
        #     asset_inventory_raw_material = AssetInventoryRawMaterial.objects.create(
        #         sku=self.raw_material_good.sku,
        #         book=self.receipt.book,
        #         unit_cost=self.unit_cost,
        #     )
        # if self.raw_material_good.raw_type == "direct":
        # asset_inventory_raw_material, created = (
        #     AssetInventoryRawMaterial.objects.update_or_create(
        #         sku=self.raw_material_good.sku,
        #         defaults={
        #             "sku": self.raw_material_good.sku,
        #             "book": self.receipt.book,
        #             "unit_cost": self.unit_cost,
        #         },
        #     )
        # )
        # elif self.raw_material_good.raw_type == "indirect":
        #     from accounting.models import EquityExpense, ExpenseCategory

        #     expense_category = ExpenseCategory.objects.get(name="Overhead")
        #     equity_expense, created = EquityExpense.objects.create(
        #         book=self.receipt.book,
        #         category=expense_category,
        #     )

        try:
            if self.raw_material_good.quantity is None:
                self.raw_material_good.quantity = self.quantity
            else:
                self.raw_material_good.quantity += self.quantity
            self.raw_material_good.save(update_fields=["quantity"])
        except Exception as e:
            raise ValueError({"error": "raw_material_good quantity did not update"})

        return super().save(*args, **kwargs)


class BillOfMaterials(models.Model):
    """
    Connects a Product to its Manufacturing Recipe.
    """
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name="bill_of_materials"
    )
    track_manufacturing = models.BooleanField(
        default=False, 
        help_text="If enabled, this product can be manufactured from raw materials."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BOM: {self.product.title}"


class BillOfMaterialsItem(models.Model):
    """
    A single raw material item within a BOM.
    """
    bill_of_materials = models.ForeignKey(
        BillOfMaterials, 
        on_delete=models.CASCADE, 
        related_name="items"
    )
    raw_material = models.ForeignKey(
        RawMaterialGood, 
        on_delete=models.CASCADE,
        related_name="bom_usages"
    )
    # Quantity required to produce 1 unit of the Product
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        help_text="Amount of raw material used to produce 1 unit of the product"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.raw_material.name} ({self.quantity} {self.raw_material.unit_of_measurement}) for {self.bill_of_materials.product.title}"


STATUS_CHOICES = [
    ("pending", "Pending"),
    ("scheduled", "Scheduled"),
    ("in_production", "In Production"),
    ("quality_check", "Quality Check"),
    ("in_repair", "In Repair"),
    ("ready", "Ready for Shipment"),
    ("shipped", "Shipped"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
]

# Order status choices for customer-facing order tracking.
# Labels go through gettext_lazy so the .po file controls the
# displayed text (English source, Turkish translations).
# The primary 4-stage flow the UI surfaces is:
#   pending → preparing → packaging → shipped
# The other statuses (confirmed, in_transit, …) remain for backward
# compatibility with existing orders and the web-checkout API.
ORDER_STATUS_CHOICES = [
    ("pending",          _("Pending")),
    ("confirmed",        _("Confirmed")),
    ("preparing",        _("Preparing")),
    ("packaging",        _("Packaging")),
    ("shipped",          _("Shipped")),
    ("in_transit",       _("In Transit")),
    ("out_for_delivery", _("Out for Delivery")),
    ("delivered",        _("Delivered")),
    ("cancelled",        _("Cancelled")),
    ("returned",         _("Returned")),
]
# The four stages we surface on the order detail page as a progress
# bar. Order matters — left to right is the natural flow.
ORDER_PRIMARY_STAGES = ("pending", "preparing", "packaging", "shipped")

# Carrier (shipping company) choices
CARRIER_CHOICES = [
    ("yurtici", "Yurtiçi Kargo"),
    ("mng", "MNG Kargo"),
    ("aras", "Aras Kargo"),
    ("ptt", "PTT Kargo"),
    ("ups", "UPS"),
    ("other", "Diğer"),
]


# Create your models here.
class Order(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Customer can be: contact (B2B), company (B2B), or web_client (B2C)
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, blank=True, null=True
    )
    web_client = models.ForeignKey(
        'authentication.WebClient', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        related_name='orders'
    )
    
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, null=True)
    qr_code_url = models.URLField(blank=True, null=True)
    
    # Payment Information (for web orders)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)  # 'iyzico_card', 'bank_transfer', etc.
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        blank=True,
        null=True
    )
    
    # Pricing Information
    original_currency = models.CharField(max_length=3, blank=True, null=True)  # 'USD', 'EUR', etc.
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paid_currency = models.CharField(max_length=3, blank=True, null=True)  # 'TRY'
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    
    # Card Information (last 4 digits only)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    card_association = models.CharField(max_length=50, blank=True, null=True)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    
    # Delivery Address
    delivery_address_title = models.CharField(max_length=100, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    delivery_city = models.CharField(max_length=100, blank=True, null=True)
    delivery_country = models.CharField(max_length=100, blank=True, null=True)
    delivery_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Billing Address
    billing_address_title = models.CharField(max_length=100, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    billing_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Guest Order Information
    is_guest_order = models.BooleanField(default=False, help_text="True if order was placed by guest (non-registered user)")
    guest_email = models.EmailField(blank=True, null=True, help_text="Email address for guest orders")
    guest_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number for guest orders")
    guest_first_name = models.CharField(max_length=100, blank=True, null=True, help_text="First name for guest orders")
    guest_last_name = models.CharField(max_length=100, blank=True, null=True, help_text="Last name for guest orders")
    
    # Shipping Tracking
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # e-Arşiv Invoice Tracking
    ettn = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        help_text="e-Arşiv Fatura Tanımlama Numarası (ETTN)"
    )
    invoice_date = models.DateField(
        null=True,
        blank=True,
        help_text="e-Arşiv Fatura oluşturma tarihi"
    )
    
    # Order Tracking for Web Orders
    order_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Müşteri sipariş numarası (DK0000001 formatında)"
    )
    order_status = models.CharField(
        max_length=32,
        choices=ORDER_STATUS_CHOICES,
        default="pending",
        help_text="Müşteriye gösterilen sipariş durumu"
    )
    carrier = models.CharField(
        max_length=50,
        choices=CARRIER_CHOICES,
        null=True,
        blank=True,
        help_text="Kargo şirketi"
    )

    # Current-account link — auto-populated on save() for manual orders
    # so cari pages can list this order's movements and so we don't
    # double-create a cari for the same customer. Web orders skip this.
    cari = models.ForeignKey(
        "current_account.CariAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Linked current account (auto-resolved from contact/company)"
    )

    def total_value(self):
        # round makes it have two decimals
        return round(sum(item.subtotal() for item in self.items.all()), 2)

        # Now whenever an OrderItem is added, updated, or deleted, the overall Order.status will update automatically.

    def gross_profit(self):
        """Sum of every item's (price - cost) × quantity. Internal-only
        metric — NEVER include in customer-facing PDFs/invoices.
        For list views, pre-fetch items with select_related('product',
        'product_variant') to avoid N+1 queries."""
        from decimal import Decimal
        total = Decimal("0")
        for it in self.items.all():
            total += it.gross_profit()
        return total.quantize(Decimal("0.01"))

    def gross_margin_pct(self):
        """Gross profit as a percentage of revenue. Returns None when
        revenue is zero so templates can hide the metric instead of
        showing 'inf'."""
        from decimal import Decimal
        rev = self.total_value() or Decimal("0")
        if rev <= 0:
            return None
        return (self.gross_profit() / Decimal(str(rev)) * Decimal("100")).quantize(Decimal("0.1"))

    def get_client(self):
        if self.contact:
            return self.contact
        elif self.company:
            return self.company
        elif self.web_client:
            return self.web_client
        return "Unknown Client"

    # below function is used in signals.py
    def update_status_from_items(self):
        item_statuses = list(self.items.values_list("status", flat=True))

        if all(s == "completed" for s in item_statuses):
            self.status = "completed"
        elif all(s == "ready" for s in item_statuses):
            self.status = "ready"
        elif "in_production" in item_statuses:
            self.status = "in_production"
        elif "pending" in item_statuses:
            self.status = "pending"
        elif any(s == "ready" for s in item_statuses):
            self.status = "partially_ready"
        else:
            self.status = "pending"

        self.save()

    def generate_order_number(self):
        """Generate order number in DK0000001 format"""
        # Get the last order with an order_number
        last_order = Order.objects.filter(
            order_number__isnull=False
        ).order_by('-id').first()
        
        if last_order and last_order.order_number:
            # Extract the number part and increment
            try:
                last_num = int(last_order.order_number.replace('DK', ''))
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        
        return f"DK{str(new_num).zfill(7)}"

    def save(self, *args, **kwargs):
        # Auto-generate order_number for web orders (if they don't have one)
        is_new = self.pk is None
        
        # First save to get ID if new
        if is_new:
            super().save(*args, **kwargs)
        
        # Generate order_number for web orders that don't have one
        if not self.order_number and self.web_client:
            self.order_number = self.generate_order_number()
            if is_new:
                # Already saved above, just update the order_number
                super().save(update_fields=['order_number'])
                return
        
        # Normal save
        if not is_new:
            super().save(*args, **kwargs)

    def __str__(self):
        if self.order_number:
            return f"Order {self.order_number} - {self.get_client()}"
        return f"Order #{self.pk} - {self.contact or self.company} "


class OrderItem(models.Model):

    # an item can added to the order later
    created_at = models.DateTimeField(auto_now_add=True)
    # we should check when the status is updated
    updated_at = models.DateTimeField(auto_now=True)

    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, blank=True, null=True
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    target_quantity_per_pack = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    # Custom Curtain Fields
    is_custom_curtain = models.BooleanField(
        default=False,
        help_text="Bu bir özel perde siparişi mi?"
    )
    custom_mounting_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('cornice', 'Korniş'),
            ('rustic', 'Rustik'),
        ],
        help_text="Montaj tipi"
    )
    custom_pleat_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('flat', 'Yatık Pile'),
            ('kanun', 'Kanun Pile'),
            ('pipe', 'Boru Pile'),
            ('water_wave', 'Su Dalgası'),
            ('american', 'Amerikan Pile'),
            ('extrafor', 'Ekstrafor'),
        ],
        help_text="Pile tipi"
    )
    custom_pleat_density = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Pile yoğunluğu (örn: 1x2, 1x2.5, 1x3)"
    )
    custom_width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Perde eni (cm)"
    )
    custom_height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Perde boyu (cm)"
    )
    custom_wing_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('single', 'Tek Kanat'),
            ('double', 'Çift Kanat'),
        ],
        help_text="Kanat tipi"
    )
    custom_fabric_used_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Kullanılan kumaş miktarı (metre)"
    )
    
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")

    def display_status(self):
        return self.status

    def update_status_from_units(self):
        print("this has been called")
        unit_statuses = list(self.units.values_list("status", flat=True))

        if all(s == "completed" for s in unit_statuses):
            self.status = "completed"
        elif all(s == "ready" for s in unit_statuses):
            self.status = "ready"
        elif "in_production" in unit_statuses:
            self.status = "in_production"
        elif "pending" in unit_statuses:
            self.status = "pending"
        elif any(s == "ready" for s in unit_statuses):
            self.status = "partially_ready"
        else:
            self.status = "pending"

        self.save()

    def subtotal(self):
        return self.price * self.quantity

    def unit_cost(self):
        """Cost per unit for gross-profit calc. Prefer the variant's
        own cost; fall back to the parent product's cost. Returns 0 if
        nothing is set so callers don't crash on None * Decimal."""
        from decimal import Decimal
        if self.product_variant and self.product_variant.variant_cost is not None:
            return self.product_variant.variant_cost
        if self.product and self.product.cost is not None:
            return self.product.cost
        return Decimal("0")

    def gross_profit(self):
        """Revenue minus cost for this single line."""
        from decimal import Decimal
        qty = self.quantity or Decimal("0")
        price = self.price or Decimal("0")
        return (price - self.unit_cost()) * qty

    def display_name(self):
        if self.product_variant:
            return f"{self.product_variant.product.title} [{self.product_variant.variant_sku}]"
        elif self.product:
            return self.product.title
        return "Unknown item"

    def display_sku(self):
        if self.product_variant:
            return self.product_variant.variant_sku
        elif self.product:
            return self.product.sku
        return "Unknown item SKU"

    # def __str__(self):
    #     if self.contact:
    #         return f"Order #{self.pk} - {self.contact.full_name}"
    #     elif self.company:
    #         return f"Order #{self.pk} - {self.company.name}"
    #     return f"Order #{self.pk}"
    def __str__(self):
        if self.product_variant:
            return f"{self.product.title} [{self.product_variant.variant_sku}] - {self.quantity} pcs"
        return f"{self.product.title} - {self.quantity} pcs"


# This will be created when the machining starts
class OrderItemUnit(models.Model):
    # an item can added to the order later
    created_at = models.DateTimeField(auto_now_add=True)
    # we should check when the status is updated
    updated_at = models.DateTimeField(auto_now=True)
    order_item = models.ForeignKey(
        OrderItem, related_name="units", on_delete=models.CASCADE
    )
    # this is the actual quantity
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    qr_code_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")

    # print save errors
    def save(self, *args, **kwargs):
        try:
            self.full_clean()  # validate fields before saving
        except ValidationError as e:
            print("💥 Validation error on OrderItemUnit:")
            print(e.message_dict)  # print field-specific errors
            traceback.print_exc()
            raise  # re-raise the error so it doesn’t fail silently

        super().save(*args, **kwargs)


# not used yet
class Production(models.Model):
    order = models.ForeignKey(
        Order, related_name="production", on_delete=models.CASCADE
    )


# GEMBA
class WorkStation(models.Model):
    name = models.CharField(max_length=150, unique=True)


class Warehouse(models.Model):
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # Optional link to an accounting Book — warehouse net worth contributes to this book
    accounting_book = models.ForeignKey(
        'accounting.Book',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouses',
        help_text="Optional: accounting book this warehouse's value is tied to"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name

    def total_value_usd(self):
        """Sum the per-product USD value across the warehouse. Uses the
        WarehouseProduct.total_cost_usd() method (with purchase_price
        fallback) so products that have a price but no explicit
        cost_usd still contribute to the rollup."""
        from decimal import Decimal
        total = Decimal('0')
        for p in self.products.all():
            v = p.total_cost_usd()
            if v:
                total += v
        return total

    def total_value_try(self):
        from decimal import Decimal
        total = Decimal('0')
        for p in self.products.all():
            v = p.total_cost_try()
            if v:
                total += v
        return total

    def product_count(self):
        return self.products.count()


class WarehouseProduct(models.Model):
    """A product instance held inside a warehouse. Mirrors marketing.Product
    but lives under a warehouse so the same SKU can have different stock per
    warehouse without coupling to the marketing catalog.
    """

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('TRY', 'TRY'),
        ('EUR', 'EUR'),
    ]

    warehouse = models.ForeignKey(
        Warehouse,
        related_name="products",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    barcode = models.CharField(max_length=64, blank=True, null=True)
    model = models.CharField(max_length=128, blank=True, null=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Original purchase price as imported from Excel
    purchase_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    purchase_currency = models.CharField(
        max_length=4, choices=CURRENCY_CHOICES, default='USD'
    )

    # Cost computed in USD and TRY (line totals = qty * unit cost)
    cost_usd = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="Unit cost in USD"
    )
    cost_try = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="Unit cost in TRY"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['warehouse', 'sku']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku or '-'}) @ {self.warehouse.name}"

    # Live USD/TRY rate fetched lazily so the model file doesn't pull
    # in accounting at import time. Cached per call.
    @staticmethod
    def _usd_try_rate():
        try:
            from accounting.services import get_exchange_rate
            from decimal import Decimal as _D
            r = get_exchange_rate("USD", "TRY")
            if r:
                return _D(str(r))
        except Exception:
            pass
        return None

    def unit_cost_usd(self):
        """Best-effort unit cost in USD. Prefers the stored cost_usd
        field; falls back to purchase_price converted from the
        purchase_currency. Returns Decimal or None."""
        from decimal import Decimal as _D
        if self.cost_usd is not None:
            return self.cost_usd
        if self.purchase_price is None:
            return None
        cur = (self.purchase_currency or "USD").upper()
        if cur == "USD" or cur == "EUR":
            # EUR ≈ USD as a coarse fallback (better than $0).
            return self.purchase_price
        if cur == "TRY":
            rate = self._usd_try_rate()
            if rate and rate > 0:
                return (self.purchase_price / rate).quantize(_D("0.0001"))
        return None

    def unit_cost_try(self):
        from decimal import Decimal as _D
        if self.cost_try is not None:
            return self.cost_try
        if self.purchase_price is None:
            return None
        cur = (self.purchase_currency or "USD").upper()
        if cur == "TRY":
            return self.purchase_price
        if cur == "USD":
            rate = self._usd_try_rate()
            if rate:
                return (self.purchase_price * rate).quantize(_D("0.01"))
        return None

    def total_cost_usd(self):
        unit = self.unit_cost_usd()
        if unit is None:
            return None
        return (self.quantity or 0) * unit

    def total_cost_try(self):
        unit = self.unit_cost_try()
        if unit is None:
            return None
        return (self.quantity or 0) * unit


class WarehouseProductRoll(models.Model):
    """A single physical roll/bale of a WarehouseProduct. Each scan
    via the warehouse camera adds one of these. The parent
    WarehouseProduct.quantity is the rolled-up sum of all roll
    meters — kept consistent in the scan view."""

    STATUS_CHOICES = [
        ("in_stock", "In stock"),
        ("partial", "Partially used"),
        ("consumed", "Fully consumed"),
    ]

    product = models.ForeignKey(
        WarehouseProduct,
        related_name="rolls",
        on_delete=models.CASCADE,
    )
    meters = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Initial length of this roll in meters",
    )
    meters_remaining = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Length still on the roll (drops as stock-outs happen)",
    )
    # The barcode printed on the label — each roll has a UNIQUE barcode
    # so we can scan it later for stock-out / order picking.
    barcode = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    lot_number = models.CharField(max_length=64, blank=True, null=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="in_stock", db_index=True,
    )
    notes = models.TextField(blank=True, null=True)
    # Camera-scan provenance
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scanned_rolls",
    )
    source_image = models.ImageField(
        upload_to="roll_scans/%Y/%m/", blank=True, null=True,
        help_text="The captured label image (kept for audit)",
    )
    ocr_raw = models.TextField(
        blank=True, null=True,
        help_text="Raw OCR text — useful for debugging misreads",
    )

    class Meta:
        ordering = ["-scanned_at"]
        indexes = [
            models.Index(fields=["product", "-scanned_at"]),
            models.Index(fields=["barcode"]),
        ]

    def __str__(self):
        return f"Roll #{self.pk} · {self.meters}m · {self.product.sku or self.product.name}"


class StockMovement(models.Model):
    """A row in the stock-movement ledger for a WarehouseProduct.
    Every change in inventory — scanned-in roll, sold/consumed meters,
    manual adjustment — emits one of these so the product detail page
    can show a date-by-date timeline."""

    TYPE_CHOICES = [
        ("in", "Stock in"),
        ("out", "Stock out"),
        ("adjustment", "Adjustment"),
    ]

    product = models.ForeignKey(
        WarehouseProduct,
        related_name="movements",
        on_delete=models.CASCADE,
    )
    roll = models.ForeignKey(
        WarehouseProductRoll,
        related_name="movements",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="The specific roll affected, when applicable",
    )
    movement_type = models.CharField(
        max_length=16, choices=TYPE_CHOICES, db_index=True,
    )
    # Always positive — sign comes from movement_type. Stored in meters.
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True, null=True)
    reference = models.CharField(
        max_length=128, blank=True, null=True,
        help_text="Free-form reference, e.g. order number, document id",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.movement_type == "in" else ("-" if self.movement_type == "out" else "±")
        return f"{sign}{self.quantity}m · {self.product.sku or self.product.name} · {self.created_at:%Y-%m-%d}"


# A machine is a physical or virtual device that performs tasks in a workstation.
# not used yet
class Machine(models.Model):
    name = models.CharField(max_length=150, unique=True)
    # maximum revolutions per minute
    max_rpm = models.PositiveIntegerField()
    # domain is the maximum number of items that can be processed in a single run
    domain = models.DecimalField(max_digits=5, decimal_places=2)
    # A machine belongs to a workstation and can have multiple machines in a workstation.
    workstation = models.ForeignKey(
        WorkStation, on_delete=models.CASCADE, related_name="machines"
    )


# not used yet
class MachineCredential(models.Model):
    name = models.CharField(max_length=150, unique=True)
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)  # Generates a 64-character hex key
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# Below is for packing


class Pack(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="packs")
    pack_number = models.PositiveIntegerField()

    class Meta:
        unique_together = ("order", "pack_number")  # prevent duplicates


class PackedItem(models.Model):
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="items")

    # One-to-One between PackItem and OrderItemUnit ensures that a unit can only be in one pack.
    order_item_unit = models.OneToOneField(OrderItemUnit, on_delete=models.CASCADE)

    # when we save the pack item, we need to update the status of the order item unit to be ready for shipping
    def save(self, *args, **kwargs):
        self.order_item_unit.status = STATUS_CHOICES[5][0]  # ready
        self.order_item_unit.save(update_fields=["status"])
        super().save(*args, **kwargs)


class PackedOrderItem(models.Model):
    """Modern packing model — packs at the OrderItem level rather than
    per-unit. Used by the simplified `order_packing_list` UI: every
    OrderItem can be in at most ONE Pack; assigning to a new Pack
    moves it, never duplicates."""
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="packed_order_items")
    order_item = models.OneToOneField(
        "OrderItem", on_delete=models.CASCADE, related_name="packed_assignment",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pack__pack_number", "id"]


# class RawMaterialUnit(models.Model):
#     raw_material = models.ForeignKey(
#         AssetInventoryRawMaterial, on_delete=models.RESTRICT, related_name="units")
