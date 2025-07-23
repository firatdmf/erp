from django.db import models
from crm.models import Contact, Company
from marketing.models import Product, ProductVariant
from django.core.exceptions import ValidationError

# uuid is used to generate unique identifiers for models.
import uuid

# below is to assign api_keys to machines
import secrets


# Create your models here.
class Order(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_production", "In Production"),
        ("quality_check", "Quality Check"),
        ("in_repair", "In Repair"),
        ("ready", "Ready for Shipment"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    created_at = models.DateTimeField(auto_now_add=True)
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

    def subtotal(self):
        return self.price * self.quantity

    def display_name(self):
        if self.product_variant:
            return f"{self.product_variant.product.title} [{self.product_variant.variant_sku}]"
        elif self.product:
            return self.product.title
        return "Unknown item"

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
    status = models.CharField(max_length=32, default="pending")

class Production(models.Model):
    order = models.ForeignKey(Order,related_name="production", on_delete=models.CASCADE)

# GEMBA
class WorkStation(models.Model):
    name = models.CharField(max_length=150, unique=True)



# A machine is a physical or virtual device that performs tasks in a workstation.
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
