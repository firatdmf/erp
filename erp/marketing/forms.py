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