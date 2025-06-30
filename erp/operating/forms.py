from django import forms
from django.forms import inlineformset_factory
from .models import *
from crm.views import search_contact

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['notes']
        # fields  = '__all__'


class OrderItemForm(forms.ModelForm):
    product_name = forms.CharField(label="Product", required=True)

    class Meta:
        model = OrderItem
        # fields = [
        #     "product",
        #     # "product_variant",
        #     "quantity",
        #     "unit_price",
        #     "status",
        #     "notes",
        # ]
        fields = "__all__"
        exclude = ["product", "product_variant"]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    #     if self.instance and self.instance.product:
    #         product = self.instance.product
    #         self.fields["product_variant"].queryset = ProductVariant.objects.filter(
    #             product=product
    #         )
    #     else:
    #         self.fields["product_variant"].queryset = ProductVariant.objects.none()


# It’s a Django helper that creates a formset (a collection of forms) for editing related objects inline with a parent object.
# Suppose you have an order with two items. The formset will show:
# A form for each existing item (pre-filled)
# One blank form for adding a new item (because extra=1)
# A delete checkbox for each item (because can_delete=True)
OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    # fields=["product", "product_variant", "quantity", "unit_price", "status", "notes"],
    # Show one blank form for adding a new OrderItem by default.
    extra=1,
    # Allow the user to delete existing OrderItems from the order in the formset.
    can_delete=True,
    can_order=True,  # Allow reordering of items in the formset
)
