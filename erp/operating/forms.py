from django import forms
from django.forms import inlineformset_factory
from .models import *
from crm.forms import WalledChoicesMixin
from crm.views import search_contact
from datetime import date
# to order the fields in the form, we can use OrderedDict
# from collections import OrderedDict


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["notes", "internal_notes"]
        # fields  = '__all__'


# class OrderItemUnitPlanForm(forms.Form):
#     pack_count = forms.IntegerField(min_value=1)
#     quantity_per_pack = forms.DecimalField(min_value=0.01)


class OrderItemUnitForm(forms.ModelForm):
    target_quantity_per_pack = forms.DecimalField(
        min_value=0.01,
        required=True,
        label="Quantity per Pack",
    )
    pack_count = forms.IntegerField(min_value=1, required=True, label="Number of Packs")

    class Meta:
        model = OrderItemUnit
        fields = (
            []
        )  # We will manually handle setting model fields like `order_item` in the view


class RawMaterialGoodReceiptForm(WalledChoicesMixin, forms.ModelForm):
    """A receipt, offering only the reader's own suppliers and books.

    The one form for the page, the drawer and its JSON save, which each
    built their own unwalled copy and so offered — and saved into — every
    book on the install.
    """
    class Meta:
        model = RawMaterialGoodReceipt
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
    def __init__(self, *args, **kwargs):
        super(RawMaterialGoodReceiptForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # The books the person behind the request may use, read the way
        # the directory wall reads them; outside a request, every book.
        from accounting.services_accounts import member_books
        from operating.audit import get_current_user

        user = get_current_user()
        if user is not None:
            self.fields["book"].queryset = member_books(getattr(user, "member", None))
    

    


class RawMaterialGoodItemForm(forms.ModelForm):
    class Meta:
        model = RawMaterialGoodItem
        fields="__all__"


# RawMaterialGoodReceiptItemFormSet = inlineformset_factory(
#     parent_model=RawMaterialGoodReceipt,
#     model=RawMaterialGoodItem,
#     form=RawMaterialGoodItemForm,
#     extra=1,
#     can_delete=True,
# )


# class OrderItemForm(forms.ModelForm):
#     # product_name = forms.CharField(label="Product", required=True)
#     # product_display = forms.CharField(label="Product", required=False, disabled=True)
#     sku = forms.CharField(label="Product SKU", required=False)

#     class Meta:
#         model = OrderItem
#         # fields = [
#         #     "product",
#         #     # "product_variant",
#         #     "quantity",
#         #     "unit_price",
#         #     "status",
#         #     "notes",
#         # ]
#         # fields = "__all__"
#         # exclude = ["product", "product_variant"]

#         fields = ["product", "product_variant", "quantity", "unit_price", "status"]
#         widgets = {
#             "product": forms.HiddenInput(),
#             "product_variant": forms.HiddenInput(),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         # Move product_sku to the first position
#         fields = OrderedDict()
#         fields["sku"] = self.fields["sku"]
#         for name, field in self.fields.items():
#             if name != "sku":
#                 fields[name] = field
#         self.fields = fields

#         # Disable product field for existing items (not extra/blank forms)
#         if self.instance and self.instance.pk:
#             self.fields["sku"].disabled = True


# # It’s a Django helper that creates a formset (a collection of forms) for editing related objects inline with a parent object.
# # Suppose you have an order with two items. The formset will show:
# # A form for each existing item (pre-filled)
# # One blank form for adding a new item (because extra=1)
# # A delete checkbox for each item (because can_delete=True)
# OrderItemFormSet = inlineformset_factory(
#     Order,
#     OrderItem,
#     form=OrderItemForm,
#     # fields=["product", "product_variant", "quantity", "unit_price", "status", "notes"],
#     # Show no blank form for adding a new OrderItem by default.
#     extra=0,
#     # Allow the user to delete existing OrderItems from the order in the formset.
#     can_delete=True,
#     # can_order=True,  # Allow reordering of items in the formset
# )
