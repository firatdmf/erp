from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseRequest, PurchaseRequestItem, PurchaseOrder, PurchaseOrderItem

class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ['department', 'priority', 'needed_by', 'reason']
        widgets = {
            'needed_by': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

PurchaseRequestItemFormSet = inlineformset_factory(
    PurchaseRequest, PurchaseRequestItem,
    fields=['product', 'raw_material', 'description', 'quantity', 'unit', 'estimated_price'],
    extra=1,
    can_delete=True
)

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'expected_delivery_date', 'shipping_address', 'currency']
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
        }

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    fields=['item_description', 'quantity', 'unit_price', 'tax_rate'],
    extra=1,
    can_delete=True
)
