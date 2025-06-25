from django import forms
from django.forms import inlineformset_factory
from .models import *


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["contact", "company", "notes"]
        # fields  = '__all__'


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    fields=["product", "product_variant", "quantity", "unit_price", "status", "notes"],
    # below adds blank rows by the quantity you define.
    extra=1,
    can_delete=True,
)


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = [
            "product",
            "product_variant",
            "quantity",
            "unit_price",
            "status",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.product:
            product = self.instance.product
            self.fields["product_variant"].queryset = ProductVariant.objects.filter(
                product=product
            )
        else:
            self.fields["product_variant"].queryset = ProductVariant.objects.none()
