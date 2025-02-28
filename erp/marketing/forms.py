# This is for the uniquness of the tag field

# class ProductForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = ['sku', 'barcode', 'title', 'description', 'media', 'collections', 'tags', 'category', 'type', 'unit_of_measurement', 'price', 'featured', 'selling_while_out_of_stock', 'weight', 'variants', 'vendor']

#     def clean_tags(self):
#         tags = self.cleaned_data.get('tags', [])
#         if len(tags) != len(set(tags)):
#             raise forms.ValidationError("Tags must be unique.")
#         return tags

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.forms import inlineformset_factory
from .models import *


class TagArrayField(SimpleArrayField):
    def __init__(self, *args, **kwargs):
        super().__init__(forms.CharField(), *args, **kwargs)


class TagArrayWidget(forms.Textarea):
    def format_value(self, value):
        if value is None:
            return ""
        return ", ".join(value)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return [tag.strip() for tag in value.split(",")]
        return []


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # fields = ['title', 'description', 'sku', 'barcode', 'price', 'cost', 'featured', 'selling_while_out_of_stock', 'weight', 'unit_of_weight', 'vendor', 'has_variants']
        fields = "__all__"

    # The input id will be "id_has_variants", this won't be saved to the database, for interactions only.
    has_variants = forms.BooleanField(
        required=False, label="Does this product have variants?"
    )
    variants = forms.CharField(widget=forms.Textarea(attrs={"rows": "5"}))

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields["variants"].widget.attrs[
            "value"
        ] = '[{"variant_sku":"", "variant_barcode":"", "variant_quantity":"", "variant_price":"", "variant_cost":""},"variant_featured":false]'


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        # fields = ['variant_sku', 'variant_barcode', 'variant_quantity', 'variant_price', 'variant_cost', 'variant_featured']
        fields = "__all__"
        widgets = {
            "product": forms.HiddenInput(),
        }


# class ProductVariantAttributeValueForm(forms.ModelForm):
#     class Meta:
#         model = ProductVariantAttributeValue
#         fields = ['attribute', 'value']


# ProductVariantFormSet = inlineformset_factory(Product, ProductVariant, form=ProductVariantForm, extra=1, can_delete=True)
# ProductVariantAttributeValueFormSet = inlineformset_factory(ProductVariant, ProductVariantAttributeValue, form=ProductVariantAttributeValueForm, extra=1, can_delete=True)
