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
        exclude = ['datasheet_url', 'primary_image']
        widgets = {
            'featured': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'selling_while_out_of_stock': forms.CheckboxInput(attrs={'class': 'switch-input'}),
        }

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
            # Evaluate into a list only if absolutely necessary, otherwise ensure fresh queryset
            self.fields['supplier'].queryset = Supplier.objects.all().order_by('company_name', 'contact_name')
        
        # If the instance has variants, set the has_variants field to True
        if self.instance and self.instance.pk:
            # Use count() instead of exists() for better compatibility with some cursor types
            if is_update and self.instance.variants.count() > 0:
                self.fields["has_variants"].initial = True

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


# ============================================================
# BLOG FORMS
# ============================================================
class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = [
            'slug', 'author', 'published_at', 'is_published',
            # English (primary)
            'title_en', 'excerpt_en', 'content_en', 'category_en',
            # Turkish
            'title_tr', 'excerpt_tr', 'content_tr', 'category_tr',
            # Russian
            'title_ru', 'excerpt_ru', 'content_ru', 'category_ru',
            # Polish
            'title_pl', 'excerpt_pl', 'content_pl', 'category_pl',
            'header_content', 'footer_content',
            # cover_image and hero_image handled manually in template via hidden inputs
        ]
        widgets = {
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'url-friendly-slug'}),
            'author': forms.TextInput(attrs={'class': 'form-input'}),
            'published_at': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            # English
            'title_en': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'English Title'}),
            'excerpt_en': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Short description in English'}),
            'content_en': forms.Textarea(attrs={'class': 'form-textarea markdown-editor', 'rows': 15, 'placeholder': 'Full content in English (Markdown supported)'}),
            'category_en': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category'}),
            # Turkish
            'title_tr': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Türkçe Başlık'}),
            'excerpt_tr': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'content_tr': forms.Textarea(attrs={'class': 'form-textarea markdown-editor', 'rows': 15}),
            'category_tr': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Kategori'}),
            # Russian
            'title_ru': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Русский заголовок'}),
            'excerpt_ru': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'content_ru': forms.Textarea(attrs={'class': 'form-textarea markdown-editor', 'rows': 15}),
            'category_ru': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Категория'}),
            # Polish
            'title_pl': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Polski tytuł'}),
            'excerpt_pl': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'content_pl': forms.Textarea(attrs={'class': 'form-textarea markdown-editor', 'rows': 15}),
            'category_pl': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Kategoria'}),
            # Code blocks
            'header_content': forms.Textarea(attrs={'class': 'form-textarea code-editor', 'rows': 5, 'placeholder': '<style>...</style>'}),
            'footer_content': forms.Textarea(attrs={'class': 'form-textarea code-editor', 'rows': 5, 'placeholder': '<script>...</script>'}),
        }



class BlogFileForm(forms.ModelForm):
    class Meta:
        model = BlogFile
        fields = ['file_url', 'file_type', 'alt_text', 'sequence']


BlogFileFormSet = inlineformset_factory(
    BlogPost, BlogFile, form=BlogFileForm, extra=1, can_delete=True
)
