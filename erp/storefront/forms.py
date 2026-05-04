from django import forms
from .models import NavMenu, HomeSection, HomeSectionCard, HomeSectionProduct, TrustBadge


class _DropImageInput(forms.ClearableFileInput):
    """Custom file input that renders as a drag-drop zone via storefront.css."""
    template_name = "storefront/widgets/drop_image.html"


# Override URLField → plain CharField rendering. The model still stores
# the value as text via URLField, but the form input becomes <input type="text">
# so relative paths like "/home/hero-c.png" don't trip browser-level
# `type="url"` validation ("Lütfen bir URL girin").
_URL_TEXT_OVERRIDES = {
    "image_url": forms.CharField(required=False, widget=forms.TextInput()),
    "feature_image_url": forms.CharField(required=False, widget=forms.TextInput()),
    "cta_href": forms.CharField(required=False, widget=forms.TextInput()),
}


class _SkipUrlValidationMixin:
    """ModelForm._post_clean runs the model's full_clean which re-runs
    URLField validators on `feature_image_url` / `image_url` / `cta_href`,
    rejecting relative paths like `/home/hero-c.png`. Exclude those fields
    from model-level validation so the form's plain CharField validation
    is the only gate."""

    _URL_FIELDS = ("feature_image_url", "image_url", "cta_href", "href")

    def _post_clean(self):
        instance = self.instance
        original_validators = {}
        for fname in self._URL_FIELDS:
            try:
                model_field = instance._meta.get_field(fname)
            except Exception:
                continue
            original_validators[fname] = list(model_field.validators)
            model_field.validators = [
                v for v in model_field.validators
                if "URLValidator" not in type(v).__name__
            ]
        try:
            super()._post_clean()
        finally:
            for fname, vs in original_validators.items():
                instance._meta.get_field(fname).validators = vs


class NavMenuForm(_SkipUrlValidationMixin, forms.ModelForm):
    image_upload = forms.ImageField(
        required=False, widget=_DropImageInput(attrs={"accept": "image/*"}),
        label="Vitrin görseli (yükle)",
        help_text="Yüklendiğinde Bunny CDN'e atılır ve URL otomatik doldurulur.",
    )
    feature_image_url = _URL_TEXT_OVERRIDES["feature_image_url"]

    class Meta:
        model = NavMenu
        fields = (
            "parent", "label_tr", "label_en", "href", "category", "swatch",
            "feature_title", "feature_meta", "feature_image_url",
            "order", "is_active",
        )


class HomeSectionForm(_SkipUrlValidationMixin, forms.ModelForm):
    image_upload = forms.ImageField(
        required=False, widget=_DropImageInput(attrs={"accept": "image/*"}),
        label="Bölüm görseli (yükle)",
        help_text="Yüklendiğinde Bunny CDN'e atılır ve URL otomatik doldurulur.",
    )
    image_url = _URL_TEXT_OVERRIDES["image_url"]
    cta_href = _URL_TEXT_OVERRIDES["cta_href"]

    class Meta:
        model = HomeSection
        fields = (
            "kind", "eyebrow_tr", "eyebrow_en", "title_tr", "title_en",
            "body_tr", "body_en", "image_url",
            "cta_label_tr", "cta_label_en", "cta_href",
            "order", "is_active",
        )


class HomeSectionCardForm(_SkipUrlValidationMixin, forms.ModelForm):
    image_url = _URL_TEXT_OVERRIDES["image_url"]
    href = _URL_TEXT_OVERRIDES["cta_href"]

    class Meta:
        model = HomeSectionCard
        fields = ("key", "label_tr", "label_en", "eyebrow_tr", "eyebrow_en",
                  "image_url", "href", "item_count", "order")


HomeSectionCardFormSet = forms.inlineformset_factory(
    HomeSection, HomeSectionCard,
    form=HomeSectionCardForm,
    extra=1, can_delete=True,
)

HomeSectionProductFormSet = forms.inlineformset_factory(
    HomeSection, HomeSectionProduct,
    fields=("product", "order"),
    extra=1, can_delete=True,
)

TrustBadgeFormSet = forms.inlineformset_factory(
    HomeSection, TrustBadge,
    fields=("icon_key", "title_tr", "title_en", "sub_tr", "sub_en", "order"),
    extra=1, can_delete=True,
)
