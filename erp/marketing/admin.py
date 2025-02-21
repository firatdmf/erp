from django.contrib import admin
from .models import *
from .forms import TagArrayField, TagArrayWidget
from django import forms
# Register your models here.


admin.site.register(Collection)

class ProductAdminForm(forms.ModelForm):
    tags = TagArrayField(widget=TagArrayWidget, required=False)

    class Meta:
        model = Product
        fields = '__all__'

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

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant)

admin.site.register(ProductVariantAttribute)
admin.site.register(ProductVariantAttributeValue)