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
        exclude = ['datasheet_url']

    # The input id will be "id_has_variants", this won't be saved to the database, for interactions only. Later we can just do Product.variants.exists()
    has_variants = forms.BooleanField(
        required=False, label="Does this product have variants?"
    )

    # If it has variants, this field will be set to True, otherwise False.
    def __init__(self, *args, **kwargs):
        # default is false, passed through the views.
        is_update = kwargs.pop("is_update", False)
        super(ProductForm, self).__init__(*args, **kwargs)
        
        # Fix cursor issues by ensuring querysets are properly evaluated
        # Force fresh queryset for supplier to avoid stale cursor references
        if 'supplier' in self.fields:
            self.fields['supplier'].queryset = Supplier.objects.all()
        
        # If the instance has variants, set the has_variants field to True
        if self.instance and self.instance.pk:
            # Use count() instead of exists() to avoid cursor issues
            if is_update and self.instance.variants.count() > 0:
                self.fields["has_variants"].initial = True
            # Force evaluation of queryset to prevent cursor issues
            self.fields["primary_image"].queryset = ProductFile.objects.filter(
                product=self.instance
            ).all()
        else:
            # For new products, show empty queryset
            self.fields["primary_image"].queryset = ProductFile.objects.none()

class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        # fields = ['variant_sku', 'variant_barcode', 'variant_quantity', 'variant_price', 'variant_cost', 'variant_featured']
        fields = "__all__"
        widgets = {
            "product": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        variant = self.instance
        variant.clean()  # Call the clean method to validate
        return cleaned_data


class ProductFileForm(forms.ModelForm):
    class Meta:
        model = ProductFile
        # fields = ["file"]
        fields = "__all__"
        # fields = ['product', 'file', 'sequence']


# # Create the inline formset for ProductFile
ProductFileFormSet = inlineformset_factory(
    Product, ProductFile, form=ProductFileForm, extra=1, can_delete=True
)

