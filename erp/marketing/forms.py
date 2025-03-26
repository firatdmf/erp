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

    # def __init__(self, *args, **kwargs):
    #     super(ProductForm, self).__init__(*args, **kwargs)


    # below are added later
    # def __init__(self, *args, **kwargs):
    #     super(ProductForm, self).__init__(*args, **kwargs)
    #     self.product_file_formset = ProductFileFormSet(instance=self.instance)

    # def save(self, commit=True):
    #     instance = super(ProductForm, self).save(commit=False)
    #     if commit:
    #         instance.save()
    #         self.product_file_formset.save()
    #     return instance

    # def is_valid(self):
    #     return (
    #         super(ProductForm, self).is_valid() and self.product_file_formset.is_valid()
    #     )

    # def clean(self):
    #     cleaned_data = super(ProductForm, self).clean()
    #     self.product_file_formset.clean()
    #     return cleaned_data


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        # fields = ['variant_sku', 'variant_barcode', 'variant_quantity', 'variant_price', 'variant_cost', 'variant_featured']
        fields = "__all__"
        widgets = {
            "product": forms.HiddenInput(),
        }


class ProductFileForm(forms.ModelForm):
    class Meta:
        model = ProductFile
        fields = ["file", "sequence"]
        # fields = "__all__"
        # fields = ['product', 'file', 'sequence']


# # Create the inline formset for ProductFile
ProductFileFormSet = inlineformset_factory(
    Product, ProductFile, form=ProductFileForm, extra=1, can_delete=True
)


# class ProductVariantAttributeValueForm(forms.ModelForm):
#     class Meta:
#         model = ProductVariantAttributeValue
#         fields = ['attribute', 'value']


# ProductVariantFormSet = inlineformset_factory(Product, ProductVariant, form=ProductVariantForm, extra=1, can_delete=True)
# ProductVariantAttributeValueFormSet = inlineformset_factory(ProductVariant, ProductVariantAttributeValue, form=ProductVariantAttributeValueForm, extra=1, can_delete=True)
