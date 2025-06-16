from django.contrib import admin
from .models import *
from .forms import TagArrayField, TagArrayWidget
from django import forms

# Register your models here.


admin.site.register(ProductCollection)
admin.site.register(ProductFile)


# Custom form for ProductFile inline to handle primary image validation
class ProductFileInlineForm(forms.ModelForm):
    class Meta:
        model = ProductFile
        fields = "__all__"

    # def clean(self):
    #     cleaned_data = super().clean()
    #     is_primary = cleaned_data.get("is_primary")
    #     product = cleaned_data.get("product")
    #     product_variant = cleaned_data.get("product_variant")

    #     # If this one is set as primary, check for duplicates
    #     if is_primary:
    #         qs = ProductFile.objects.all()
    #         if self.instance.pk:
    #             qs = qs.exclude(pk=self.instance.pk)

    #         if product:
    #             qs = qs.filter(product=product, is_primary=True)
    #         elif product_variant:
    #             qs = qs.filter(product_variant=product_variant, is_primary=True)

    #         if qs.exists():
    #             raise ValidationError("Only one image can be marked as primary.")

    #     return cleaned_data


class ProductAdminForm(forms.ModelForm):
    tags = TagArrayField(widget=TagArrayWidget, required=False)

    class Meta:
        model = Product
        fields = "__all__"

    # def clean(self):
    #     cleaned_data = super().clean()
    #     product = self.instance
    #     product.clean()  # Call the clean method to enforce model validation
    #     return cleaned_data


class ProductFileInline(admin.TabularInline):
    model = ProductFile
    form = ProductFileInlineForm
    extra = 1  # Number of extra forms to display
    # fields = ("file", "sequence", "is_primary")
    fields = ("file", "sequence")
    ordering = ["sequence"]


class ProductVariantInLine(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductFileInline, ProductVariantInLine]
    list_display = ("title", "sku", "price", "featured", "selling_while_out_of_stock")
    search_fields = ("title", "sku", "barcode")
    list_filter = ("featured", "selling_while_out_of_stock", "collections")
    # I added below to show the primary image in the admin interface.
    raw_id_fields = ["primary_image"]
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
        fields = "__all__"

    # def clean(self):
    #     cleaned_data = super().clean()
    #     variant = self.instance
    #     variant.clean()  # Call the clean method to enforce model validation
    #     return cleaned_data


# Admin for ProductVariant
class ProductVariantAdmin(admin.ModelAdmin):
    form = ProductVariantAdminForm  # Use the custom form with validation
    list_display = (
        "variant_sku",
        "variant_price",
        "variant_quantity",
        "product",
        "variant_featured",
        "attribute_summary",
    )
    search_fields = ("variant_sku", "product__sku", "variant_barcode")
    readonly_fields = ("attribute_summary",)


admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)

admin.site.register(ProductVariantAttribute)
admin.site.register(ProductVariantAttributeValue)

admin.site.register(ProductCategory)


class ProductFileAdminForm(forms.ModelForm):
    upload = forms.ImageField(required=False, label="Upload Image")

    class Meta:
        model = ProductFile
        fields = ["product", "product_variant", "is_primary", "sequence", "upload"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload_file = self.cleaned_data.get("upload")
        if upload_file:
            instance.upload = upload_file  # Set the temporary attribute
        if commit:
            instance.save()
        return instance


from django.contrib import admin


class ProductFileAdmin(admin.ModelAdmin):
    form = ProductFileAdminForm
    list_display = (
        "id",
        "product",
        "product_variant",
        "file_url",
        "is_primary",
        "sequence",
    )


