from django.db import models
from django.conf import settings
from crm.models import Supplier
from marketing.models import Product, ProductVariant
from operating.models import RawMaterialGood

class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('ordered', 'Ordered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchase_requests')
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    requested_date = models.DateField(auto_now_add=True)
    needed_by = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True, help_text="Justification for the request")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_requests')
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PR-{self.pk} by {self.requester} ({self.status})"

class PurchaseRequestItem(models.Model):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, help_text="Select if buying a finished product")
    raw_material = models.ForeignKey(RawMaterialGood, on_delete=models.SET_NULL, null=True, blank=True, help_text="Select if buying raw material")
    description = models.CharField(max_length=255, blank=True, help_text="Description if item not in system")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default='unit')
    estimated_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        item_name = self.description or (self.raw_material.name if self.raw_material else str(self.product))
        return f"{self.quantity} x {item_name}"

class RequestForQuotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Suppliers'),
        ('closed', 'Closed'),
    ]

    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    suppliers = models.ManyToManyField(Supplier, related_name='rfqs')
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    requests = models.ManyToManyField(PurchaseRequest, related_name='rfqs', blank=True)

    def __str__(self):
        return self.title

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed by Supplier'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD') # Should link to Currency model ideally
    shipping_address = models.TextField(blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO-{self.pk} - {self.supplier}"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    # Link back to the original request item if applicable
    request_item = models.ForeignKey(PurchaseRequestItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='po_items')
    
    # Redundant but necessary fields for the PO snapshot
    item_description = models.CharField(max_length=255) # Snapshot of item name
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.item_description}"
