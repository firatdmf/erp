from django import forms
from django.forms import inlineformset_factory
from .models import *


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['contact', 'company', 'notes']

OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    fields=['product', 'quantity', 'unit_price', 'status', 'notes'],
    # below adds blank rows by the quantity you define.
    extra=1,
    can_delete=True,
)