from django.contrib import admin
from .models import *
from .forms import TagArrayField, TagArrayWidget
from django import forms
# Register your models here.


admin.site.register(ProductCollection)
admin.site.register(ProductFile)

class ProductAdminForm(forms.ModelForm):
    tags = TagArrayField(widget=TagArrayWidget, required=False)

    class Meta:
        model = Product
        fields = '__all__'
    
    # def clean(self):
    #     cleaned_data = super().clean()
    #     product = self.instance
    #     product.clean()  # Call the clean method to enforce model validation
    #     return cleaned_data

class ProductFileInline(admin.TabularInline):
    model = ProductFile
    extra = 1  # Number of extra forms to display


class ProductVariantInLine(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductFileInline, ProductVariantInLine]
    list_display = ('title', 'sku', 'price', 'featured', 'selling_while_out_of_stock')
    search_fields = ('title', 'sku', 'barcode')
    list_filter = ('featured', 'selling_while_out_of_stock', 'collections')
    form = ProductAdminForm  # Use the custom form with validation

    # # The save_model method is overridden in ProductAdmin to call full_clean() before saving the object, ensuring the validation is triggered.
    # def save_model(self, request, obj, form, change):
    #     try:
    #         obj.full_clean()  # Call full_clean to ensure validation before save
    #         super().save_model(request, obj, form, change)
    #     except ValidationError as e:
    #         # Handle the error if needed (e.g., display a message)
    #         raise ValidationError(e)

# Custom admin for ProductVariant to include validation logic
class ProductVariantAdminForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = '__all__'

    # def clean(self):
    #     cleaned_data = super().clean()
    #     variant = self.instance
    #     variant.clean()  # Call the clean method to enforce model validation
    #     return cleaned_data


# Admin for ProductVariant
class ProductVariantAdmin(admin.ModelAdmin):
    form = ProductVariantAdminForm  # Use the custom form with validation
    list_display = ('variant_sku', 'variant_price', 'variant_quantity', 'product', 'variant_featured')
    search_fields = ('variant_sku', 'product__sku', 'variant_barcode')

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)

admin.site.register(ProductVariantAttribute)
admin.site.register(ProductVariantAttributeValue)

admin.site.register(ProductCategory)