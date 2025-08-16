import traceback
from django.db import models
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

# from accounting.models import AssetInventoryRawMaterial
# uuid is used to generate unique identifiers for models.
import uuid

# below is to assign api_keys to machines
import secrets


# class FinishedGood(models.Model):
#     # book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="finished_goods")
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateField(blank=True, null=True)
#     order = models.ForeignKey(
#         "Order", on_delete=models.CASCADE, related_name="finished_goods"
#     )
#     product = models.ForeignKey(
#         Product,
#         on_delete=models.CASCADE,
#         blank=False,
#         null=False,
#         related_name="finished_goods",
#     )
#     product_variant = models.ForeignKey(
#         ProductVariant,
#         on_delete=models.CASCADE,
#         blank=True,
#         null=True,
#         related_name="finished_goods",
#     )
#     quantity = models.DecimalField(
#         max_digits=10, decimal_places=2, null=True, blank=True
#     )
#     warehouse = models.ForeignKey(
#         "Warehouse",
#         on_delete=models.RESTRICT,
#         blank=True,
#         null=True,
#         related_name="finished_goods",
#     )


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
        default=("direct", "Direct"),
    )

    name = models.CharField(null=False, blank=False)

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
        default=("units", "Unit"),
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
        return f"{self.name} | {(self.sku) if self.sku != self.pk else self.supplier_sku}"


from accounting.models import Book


class RawMaterialGoodReceipt(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "receipt_number"],
                name="unique_supplier_receipt_number",
            )
        ]

    # should be approved by accounting, and operating supervisor for quality.
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(blank=True, null=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.RESTRICT, null=False, blank=False
    )
    receipt_number = models.CharField(blank=False, null=False, max_length=50)
    approved = models.BooleanField(default=False)

    @property
    def amount(self):
        total = 0
        for item in self.items:
            total += item.cost
        return total

    def __str__(self):
        return f"{self.book} | on: {self.date} From: {self.supplier} with Receipt #: {self.receipt_number} | Approved: {self.approved}"


class RawMaterialGoodItem(models.Model):

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
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        from accounting.models import AssetInventoryRawMaterial

        self.full_clean()
        try:
            # asset_inventory_raw_material = get_object_or_404(AssetInventoryRawMaterial, sku=self.raw_material_good.sku)
            asset_inventory_raw_material = AssetInventoryRawMaterial.objects.get(
                sku=self.raw_material_good.sku
            )
        except AssetInventoryRawMaterial.DoesNotExist:
            asset_inventory_raw_material = AssetInventoryRawMaterial.objects.create(
                sku=self.raw_material_good.sku,
                book=self.receipt.book,
                unit_cost=self.unit_cost,
            )

        try:
            self.raw_material_good.quantity += self.quantity
        except Exception as e:
            raise ValueError({"error":"raw_material_good quantity did not update"})

        return super().save(*args, **kwargs)


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


# Create your models here.
class Order(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # should be linked to an either contact or company
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, blank=True, null=True
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, null=True)
    qr_code_url = models.URLField(blank=True, null=True)  # ✅ Add this line

    def total_value(self):
        # round makes it have two decimals
        return round(sum(item.subtotal() for item in self.items.all()), 2)

        # Now whenever an OrderItem is added, updated, or deleted, the overall Order.status will update automatically.

    def get_client(self):
        if self.contact:
            return self.contact
        elif self.company:
            return self.company
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

    def __str__(self):
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

    def __str__(self):
        return self.name


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


# class RawMaterialUnit(models.Model):
#     raw_material = models.ForeignKey(
#         AssetInventoryRawMaterial, on_delete=models.RESTRICT, related_name="units")
