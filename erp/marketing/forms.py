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

class TagArrayField(SimpleArrayField):
    def __init__(self, *args, **kwargs):
        super().__init__(forms.CharField(), *args, **kwargs)

class TagArrayWidget(forms.Textarea):
    def format_value(self, value):
        if value is None:
            return ''
        return ', '.join(value)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return [tag.strip() for tag in value.split(',')]
        return []