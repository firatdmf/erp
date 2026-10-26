import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.forms import inlineformset_factory
from django.utils.translation import gettext as _, gettext_lazy

_lazy_title_tr = gettext_lazy("Turkish title")
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
        # Collections are typed by name below (collection_names), not picked
        # from the model's multiple-choice list, which the page never drew.
        # Price and cost live on the variants: every product has at least
        # one, so the product's own two columns are read by nothing and
        # are on their way out.
        exclude = ['datasheet_url', 'primary_image', 'collections', 'price', 'cost',
                   'profit_margin']
        widgets = {
            'featured': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'selling_while_out_of_stock': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'gsm': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'placeholder': 'e.g. 320'}),
        }

    # The input id will be "id_has_variants", this won't be saved to the database, for interactions only. Later we can just do Product.variants.exists()
    has_variants = forms.BooleanField(
        required=False, label="Does this product have variants?"
    )

    # What the variants are priced and cost at, for the Pricing card; set
    # in __init__ for a saved product — see there.
    variants_price_low = None
    variants_price_high = None
    variants_cost = None
    variants_cost_is_stored = False

    # A single item: a product with no options. On screen it has no variant
    # table, just these boxes; underneath it is one variant, which they are
    # saved to (save_single_item). Its price is not typed: it is worked out
    # from the cost (marketing/pricing.py) and shown as item_price_live. The page posts single_item=1
    # while it is in that mode — adding an option leaves it.
    item_sku = forms.CharField(
        required=False, max_length=ProductVariant._meta.get_field("variant_sku").max_length,
        label=gettext_lazy("Item SKU"),
        widget=forms.TextInput(attrs={"class": "form-input", "autocomplete": "off"}))
    item_cost = forms.DecimalField(
        required=False, min_value=0, max_digits=10, decimal_places=2,
        label=gettext_lazy("Cost per item"),
        widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "placeholder": "0.00"}))
    single_item = False
    single_variant = None
    item_cost_computed = None
    item_price_live = None

    collection_names = forms.CharField(
        required=False,
        label=gettext_lazy("Collections"),
        widget=forms.TextInput(attrs={
            'class': 'form-input', 'list': 'collectionChoices',
            'placeholder': 'Bridal, Summer 2026', 'autocomplete': 'off'}),
    )

    def clean_collection_names(self):
        """The collections typed, comma between them, each once whatever its
        capitals."""
        names, seen = [], set()
        for name in (self.cleaned_data.get('collection_names') or '').split(','):
            name = " ".join(name.split())
            if name and name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)
        return names

    def _save_m2m(self):
        """Put the product in the collections typed: one already there by
        that name (any capitals), or a new one."""
        super()._save_m2m()
        if 'collection_names' not in self.cleaned_data:
            return
        chosen = []
        for name in self.cleaned_data['collection_names']:
            collection = ProductCollection.objects.filter(title__iexact=name).order_by('id').first()
            chosen.append(collection or ProductCollection.objects.create(title=name))
        self.instance.collections.set(chosen)

    def clean_tags(self):
        """Each tag once, lower case, as the storefront reads them
        ("Embroidery" would not be found by its "embroidery")."""
        tags = []
        for tag in self.cleaned_data.get('tags') or []:
            tag = " ".join(str(tag or "").lower().split())
            if tag and tag not in tags:
                tags.append(tag)
        return tags

    # If it has variants, this field will be set to True, otherwise False.
    def __init__(self, *args, **kwargs):
        # default is false, passed through the views.
        is_update = kwargs.pop("is_update", False)
        super(ProductForm, self).__init__(*args, **kwargs)
        self.is_update = is_update
        
        # Fix cursor issues by ensuring querysets are properly evaluated
        # Force fresh queryset for supplier to avoid stale cursor references
        if 'supplier_account' in self.fields:
            # Evaluate into a list only if absolutely necessary, otherwise ensure fresh queryset
            from accounting.models_accounts import CurrentAccount
            from accounting.services_accounts import get_default_book
            self.fields['supplier_account'].queryset = (
                CurrentAccount.objects
                .filter(book=get_default_book(), is_active=True)
                .order_by('name')
            )
        
        # The collections the product is in, as typed names, and every
        # collection there is, offered as the box is typed into.
        self.collection_titles = list(
            ProductCollection.objects.exclude(title__isnull=True).exclude(title='')
            .order_by('title').values_list('title', flat=True))
        if self.instance and self.instance.pk:
            self.fields['collection_names'].initial = ", ".join(
                c.title for c in self.instance.collections.order_by('title') if c.title)

        # Tags are typed as one line, comma between them ("embroidery, sheer").
        if 'tags' in self.fields:
            self.fields['tags'].widget.attrs.update({
                'class': 'form-input',
                'placeholder': 'embroidery, sheer',
            })

        # Every product is in a group: its price multiplier comes from there.
        if 'category' in self.fields:
            self.fields['category'].required = True

        # No options and at most one variant: shown as a single item.
        variants = list(self.instance.variants.prefetch_related(
            "product_variant_attribute_values")) if self.instance.pk else []
        if len(variants) <= 1 and not any(
                v.product_variant_attribute_values.all() for v in variants):
            self.single_item = True
            if variants:
                self.single_variant = variants[0]
                self.fields["item_sku"].initial = variants[0].variant_sku
                self.item_price_live = variants[0].live_price
                self.fields["item_cost"].initial = variants[0].variant_cost
                # Priced stock on hand says what it cost; nobody types that.
                self.item_cost_computed = variants[0].stock_cost

        # If the instance has variants, set the has_variants field to True
        if self.instance and self.instance.pk:
            # Use count() instead of exists() for better compatibility with some cursor types
            if is_update and self.instance.variants.count() > 0:
                self.fields["has_variants"].initial = True
                # Price and cost are typed on each variant. The card shows
                # what they come to: the lowest and highest variant price,
                # and the cost of the variants' stock, weighted by what is
                # on the floor and valued exactly as the balance sheet
                # carries it — with nothing in stock, the plain mean of the
                # variants' stored costs, shown as such.
                prices = [v.live_price for v in attach_live_costs(self.instance.variants.all())
                          if v.live_price is not None]
                if prices:
                    self.variants_price_low, self.variants_price_high = min(prices), max(prices)
                from accounting.services_ledger import inventory_average_cost
                from operating.models import WarehouseProductItem
                self.variants_cost = inventory_average_cost(
                    WarehouseProductItem.objects.filter(
                        product__catalog_variant__product=self.instance))
                if self.variants_cost is None:
                    stored = [v.variant_cost for v in self.instance.variants.all()
                              if v.variant_cost is not None]
                    if stored:
                        self.variants_cost = (sum(stored) / len(stored)).quantize(Decimal("0.0001"))
                        self.variants_cost_is_stored = True

    @property
    def example_cost(self):
        """The cost the multiplier box's preview works an example price
        from: this product's own, where there is one."""
        cost = self.item_cost_computed or self.variants_cost
        if cost is None and self.single_variant is not None:
            cost = self.single_variant.variant_cost
        return "" if cost is None else format(Decimal(cost).quantize(Decimal("0.01")), "f")

    def clean_price_multiplier(self):
        """A formula the price can be worked out with, or blank for the
        group's (marketing/pricing.py)."""
        from .pricing import parse_multiplier
        text = (self.cleaned_data.get("price_multiplier") or "").strip()
        if text:
            try:
                parse_multiplier(text)
            except ValueError:
                raise forms.ValidationError(
                    _("Type what the cost is multiplied by, e.g. 4/3 or 1.5."))
        return text

    def clean_sku(self):
        """A NEW product's SKU is stored in capitals and carries no dot.

        The dot is what separates a variant's SKU from its parent's
        (K24644.BEYAZ-140), so the parent cannot contain one. Products that
        already exist keep whatever SKU they have; this is a rule for the
        catalog from here on, not a cleanup.
        """
        sku = (self.cleaned_data.get("sku") or "").strip()
        if self.is_update:
            return sku
        sku = sku.upper()
        if "." in sku:
            raise forms.ValidationError(
                _("A product SKU cannot contain a dot — the dot separates it from its variants' SKUs."))
        return sku

    def clean(self):
        """Refuse a negative variant price or cost before anything is saved.

        The variants arrive as JSON in the same POST, outside any form field,
        and the view writes them with bulk_update after saving the product —
        so without this the database constraint would reject them halfway
        through, after the product itself had already been written.
        """
        cleaned_data = super().clean()
        negative = sorted(_skus_with_negative_money(self.data.get("variants_json")))
        if negative:
            raise forms.ValidationError(
                _("Variant price and cost cannot be negative: %(skus)s")
                % {"skus": ", ".join(negative)}
            )
        parent = cleaned_data.get("sku")
        if parent:
            off = _skus_off_the_parent(self.data.get("variants_json"), parent)
            if self.is_update:
                # A variant saved before the rule on some other SKU may keep
                # it; one typed or changed now follows the rule.
                off -= set(self.instance.variants.values_list("variant_sku", flat=True))
            off = sorted(off)
            if off:
                raise forms.ValidationError(
                    _("Each variant SKU must be the product SKU, a dot, then the "
                      "variant's own part in capitals (%(example)s): %(skus)s")
                    % {"example": f"{parent}.{_('WHITE-140')}", "skus": ", ".join(off)}
                )
        # A featured variant is on sale, so it has to cost something: its
        # stock says what, and where it has none on hand (made to order,
        # sold out) somebody must. One nobody sells can wait for its cost.
        uncosted = sorted(self._featured_variants_without_a_cost())
        if uncosted:
            raise forms.ValidationError(
                _("Enter a cost for these featured variants — they have no stock to "
                  "take one from: %(skus)s") % {"skus": ", ".join(uncosted)}
            )
        if self._posted_single_item():
            self._clean_single_item(cleaned_data)
        # What is sold is always a variant — a single item is a product with
        # one — so its SKU, price and cost have somewhere to live.
        elif not self._has_variants(cleaned_data):
            raise forms.ValidationError(
                _("Add at least one variant. A single item has one, with no options."))
        return cleaned_data

    def _featured_variants_without_a_cost(self):
        """SKUs of the posted variants that are featured, carry no cost,
        and have no priced stock to read one from."""
        from .models import stock_costs
        known = ({v.pk: v.variant_sku for v in self.instance.variants.all()}
                 if self.instance.pk else {})
        computed = set(stock_costs(known))
        computed_skus = {known[pk] for pk in computed}
        found = set()
        for variant in _variant_dicts(self.data.get("variants_json")):
            if not variant.get("variant_featured"):
                continue
            if variant.get("variant_cost") not in (None, ""):
                continue
            sku = str(variant.get("variant_sku") or "")
            if variant.get("variant_id") in computed or sku in computed_skus:
                continue
            found.add(sku or "?")
        return found

    def _posted_single_item(self):
        return self.data.get("single_item") == "1"

    def _clean_single_item(self, cleaned_data):
        """The single item's SKU is needed, and is its own; a featured one
        with nothing in stock needs a cost, as any featured variant does."""
        sku = (cleaned_data.get("item_sku") or "").strip()
        if not sku:
            self.add_error("item_sku", _("Enter the item's SKU — stock, barcodes and orders use it."))
            return
        taken = ProductVariant.objects.filter(variant_sku=sku)
        if self.single_variant is not None:
            taken = taken.exclude(pk=self.single_variant.pk)
        if taken.exists():
            self.add_error("item_sku", _("Another variant already has this SKU."))
        cleaned_data["item_sku"] = sku
        if (self.item_cost_computed is None and cleaned_data.get("item_cost") is None
                and "item_cost" not in self.errors
                and (self.single_variant is None or self.single_variant.variant_featured)):
            self.add_error("item_cost", _("Enter the cost — nothing is in stock to take one from."))

    def save_single_item(self, product):
        """Write the single item's boxes to its one variant, creating it
        for a new product. Called by the views after the variants are
        handled, so a new product's "no variants" pass cannot remove it."""
        if not self._posted_single_item():
            return None
        variant = self.single_variant
        if variant is None:
            variant = product.variants.first() if product.variants.count() == 1 else None
        if variant is None:
            variant = ProductVariant(product=product)
        variant.variant_sku = self.cleaned_data["item_sku"]
        if self.item_cost_computed is None:
            variant.variant_cost = self.cleaned_data.get("item_cost")
        variant.save()
        return variant

    def _has_variants(self, cleaned_data):
        """Whether the product will have variants once this form is saved.
        The page posts them as variants_json; a form built without it (an
        import, a test) is judged by the switch and by what the product
        already has."""
        if "variants_json" in self.data:
            if _variant_dicts(self.data.get("variants_json")):
                return True
            # An empty list leaves the saved variants alone (handle_variants
            # deletes only what it is told to); "delete all" does not.
            try:
                payload = json.loads(self.data.get("variants_json") or "[]")
            except (TypeError, ValueError):
                payload = []
            if isinstance(payload, dict) and payload.get("delete_all_variants"):
                return False
            return bool(self.instance.pk and self.instance.variants.exists())
        if cleaned_data.get("has_variants"):
            return True
        return bool(self.instance.pk and self.instance.variants.exists())


def _variant_dicts(variants_json):
    """The variant dicts in a product form's variants_json. Unparseable
    input yields nothing; handle_variants deals with that as it always has."""
    try:
        data = json.loads(variants_json or "[]")
    except (TypeError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("product_variant_list", [])
    if not isinstance(data, list):
        return []
    return [v for v in data if isinstance(v, dict)]


def _skus_off_the_parent(variants_json, parent):
    """The variant SKUs that do not read PARENT.SUFFIX — the parent SKU (in
    any case: an old product's may be lower case), a dot, and a non-empty
    suffix already in capitals. See ProductForm.clean.

    A variant with no option values (a single item's one variant) has no
    suffix to build: its SKU is typed by hand, and only has to be there."""
    prefix = f"{parent}.".upper()
    found = set()
    for variant in _variant_dicts(variants_json):
        sku = str(variant.get("variant_sku") or "")
        # The page always sends the variant's option values; an empty set
        # is a variant with no options.
        values = variant.get("variant_attribute_values")
        if isinstance(values, dict) and not any(str(v or "").strip() for v in values.values()):
            if not sku.strip():
                found.add("?")
            continue
        suffix = sku[len(prefix):] if sku.upper().startswith(prefix) else ""
        if not suffix.strip() or suffix != suffix.upper():
            found.add(sku or "?")
    return found


def _skus_with_negative_money(variants_json):
    """The SKUs in a product form's variants_json whose price or cost is
    below zero. Blank and unparseable values are not this check's business;
    handle_variants deals with those as it always has."""
    found = set()
    for variant in _variant_dicts(variants_json):
        for key in ("variant_price", "variant_cost"):
            value = variant.get(key)
            if value in (None, ""):
                continue
            try:
                if Decimal(str(value)) < 0:
                    found.add(str(variant.get("variant_sku") or "?"))
            except (InvalidOperation, ValueError):
                continue
    return found

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
            'title_tr': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _lazy_title_tr}),
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
        }



class BlogFileForm(forms.ModelForm):
    class Meta:
        model = BlogFile
        fields = ['file_url', 'file_type', 'alt_text', 'sequence']


BlogFileFormSet = inlineformset_factory(
    BlogPost, BlogFile, form=BlogFileForm, extra=1, can_delete=True
)
