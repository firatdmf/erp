from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _lz
import os
import time

# Standardized labels used to identify the nature and format of a file's content
import mimetypes
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from . import units
from .attributes import normalize_attribute_name, normalize_attribute_value


def _directory_manager():
    # crm.models imports nothing of marketing's, so this is safe at import
    # time; kept in a function so the dependency reads as deliberate.
    from crm.models import DirectoryManager
    return DirectoryManager()


def _reachable_products(directory_ids):
    """The products someone reading `directory_ids` has, as a subquery —
    for the models that hang off a product and are walled by it."""
    from crm.models import reachable_from
    return Product.everywhere.filter(reachable_from(Product, directory_ids))


class ProductPartManager(models.Manager):
    """Default manager for what belongs to a product — a variant, a file.

    A product is kept in one directory (see Product.directory) and its
    parts go where it goes: an id typed into a variant's or an image's
    URL finds nothing unless the product behind it is one the reader may
    open. `paths` are the foreign keys that lead to the product; a row
    that names none is nobody's and passes.
    """

    def __init__(self, *paths):
        super().__init__()
        self.paths = paths

    def get_queryset(self):
        from crm.models import visible_directory_ids
        qs = super().get_queryset()
        ids = visible_directory_ids()
        if ids is None:
            return qs
        mine = _reachable_products(ids)
        reach = models.Q()
        nobody = models.Q()
        for path in self.paths:
            reach |= models.Q(**{f"{path}__in": mine})
            nobody &= models.Q(**{f"{path}__isnull": True})
        return qs.filter(reach | nobody)



# Create your functions here.
# --------------------------------------------------------------------------------------------
# FILE SAVER FUNCTION FOR THE PRODUCTS


def product_file_directory_path(instance, filename):
    """Path for new uploads.

    Anchored on the stable product.id / variant.id rather than the
    user-editable SKU — that way renaming `variant_sku` (or even the
    parent product's sku) doesn't orphan future uploads from the
    earlier-uploaded ones. Existing file_url values in ProductFile are
    untouched; only NEW uploads use this layout.
    """
    pid = getattr(instance.product, "pk", None) or "no-product"
    if instance.product_variant_id:
        vid = instance.product_variant_id
        return f"product_files/p{pid}/v{vid}/{filename}"
    return f"product_files/p{pid}/{filename}"


def product_category_directory_path(instance, filename):
    return f"product_categories/{instance.name}/{filename}"


# -----------------------------------------------------------------
# def weight_unit_choices():
#     return [('lb','lb'),('oz','oz'),('kg','kg'),('g','g')]


def validate_file_size(file):
    filesize = file.size
    # You need to put in bytes:
    # 10 MB limit
    size_threshold = 10485760
    if filesize > size_threshold:
        raise ValidationError("The maximum file size that can be uploaded is 10MB")
    return file


def validate_file_type(file):
    valid_mime_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/avif",
        "video/mp4",
        "video/hls",
        "audio/mpeg",
    ]
    mime_type, encoding = mimetypes.guess_type(file.name)
    if mime_type not in valid_mime_types:
        raise ValidationError(
            "Unsupported file type. Allowed types are: jpg, png, gif, webp, avif, mp4, hls, mp3."
        )
    return file


def validate_image_type(image):
    valid_mime_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/avif",
    ]
    mime_type, encoding = mimetypes.guess_type(image.name)
    if mime_type not in valid_mime_types:
        raise ValidationError(
            "Unsupported file type. Allowed types are: jpg, png, gif, webp, avif, mp4, hls, mp3."
        )
    return image


@classmethod
def bulk_delete_with_files(cls, queryset):
    """
    Deletes all ProductFile instances in the queryset,
    ensuring files are removed from the filesystem.
    """
    for obj in queryset:
        obj.delete()


# ---------------------------------------------------------------------------------------------

# Create your models here.


class ProductCollection(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to=product_file_directory_path,
        null=True,
        blank=True,
        validators=[validate_file_size, validate_image_type],
    )

    def __str__(self):
        return f"{self.title}"


class ProductCategory(models.Model):
    """Product group (bed, fabric, curtain…). Beyond classification, the group
    is the DEFAULTS layer for its products: pricing margin, order rules and
    care texts are set once here and every product in the group inherits
    them unless it sets its own override (see Product.effective_*)."""

    class Meta:
        verbose_name_plural = "Product Categories"

    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    description = models.TextField(null=True, blank=True)

    image_url = models.URLField(null=True, blank=True)

    # Shown on the B2B storefront? Lets a whole group be pulled offline
    # without touching each product's featured flag.
    is_active = models.BooleanField(default=True)

    # Pricing: % profit margin applied on top of cost when pricing the
    # group's products (price = cost * (1 + margin/100)). The group page
    # can bulk-apply this to every costed product/variant in the group.
    profit_margin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text=_lz("Margin % — added on top of cost (price = cost × (1 + margin/100))"),
    )

    # Order rules — defaults for the B2B storefront.
    minimum_order_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_lz("Minimum order quantity for products in this group (can be overridden per product)"),
    )
    lead_time_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_lz("Estimated supply/delivery time (days)"),
    )

    # Care text — entered once per group, pulled by every product that
    # doesn't define its own (products keep theirs inside the description
    # translations JSON). Bilingual like the product-level texts.
    care_instructions = models.TextField(null=True, blank=True)           # EN
    care_instructions_tr = models.TextField(null=True, blank=True)

    # Customs tariff (GTIP/HS) code — the group usually shares one; used on
    # export paperwork for foreign B2B customers.
    hs_code = models.CharField(max_length=20, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.name = self.name.lower().strip().replace(" ", "_")
        image_file = getattr(self, "_image_file", None)
        if image_file:
            from .utils.bunny_storage import upload_to_bunny
            folder = f"media/product_categories/{self.name}"
            path = f"{folder}/{image_file.name}"
            self.image_url = upload_to_bunny(image_file, path)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

    def variant_attribute_names(self):
        """The attributes this group's variants are described by, in order —
        what a new product in the group is asked (see CategoryVariantAttribute)."""
        return list(self.variant_attribute_presets.order_by("position", "id")
                    .values_list("attribute__name", flat=True))


class CategoryVariantAttribute(models.Model):
    """One attribute in a product group's preset: the questions a new
    product of the group is asked about each variant (fabric: color,
    model…), in order. Edited on the product group page; a product can
    still describe its variants with attributes beyond its group's."""

    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE,
                                 related_name="variant_attribute_presets")
    attribute = models.ForeignKey("ProductVariantAttribute", on_delete=models.CASCADE,
                                  related_name="category_presets")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["category", "attribute"],
                                    name="uniq_category_variant_attribute"),
        ]

    def __str__(self):
        return f"{self.category.name}: {self.attribute.name}"


# How long a SKU may be, for products and variants alike. Was 20, which is
# less than it sounds: "PETEK.FONLUK KUMAŞ." is 19 characters on its own, so
# a code like PETEK.FONLUK KUMAŞ.200.310 was silently cut to one character
# past the prefix and then de-duplicated into .1/.2/.3. Matches
# WarehouseProduct.sku so the two sides can always hold the same string.
SKU_MAX_LENGTH = 64


class Product(models.Model):
    created_at = models.DateTimeField(auto_now=True, blank=False, null=False)
    QUANTITY_UNIT_TYPE_CHOICES = [
        ("units", "Unit"),
        ("mt", "Meter"),
        ("kg", "Kilogram"),
    ]
    WEIGHT_UNIT_TYPE_CHOICES = [("lb", "lb"), ("oz", "oz"), ("kg", "kg"), ("g", "g")]

    # Whose product this is. An install carries several businesses, and
    # each keeps its own catalogue the way it keeps its own customers: a
    # product is in one directory (crm.Directory), every book reads one,
    # and people see the products of the books they are assigned — in the
    # catalogue, in the order form's search, and by id. Two books of one
    # business share a directory and so a catalogue. A superuser, and the
    # storefront (which nobody is signed in to), see all of them.
    #
    # Not editable, so no form offers it: a product is filed by where its
    # author works (save() below), and shown to another business only by
    # sharing it (share_with).
    directory = models.ForeignKey(
        "crm.Directory", on_delete=models.PROTECT, related_name="products",
        editable=False,
    )
    shared_with = models.ManyToManyField(
        "crm.Directory", blank=True, related_name="shared_products", editable=False,
    )

    title = models.CharField(max_length=255, null=False, blank=False, db_index=True)

    # This can be implement and used as html later.
    description = models.TextField(null=True, blank=True)

    # Stock Keeping Unit
    # This should be unique also
    # If the product has a variant, this should be null
    sku = models.CharField(
        max_length=SKU_MAX_LENGTH, null=True, blank=False, unique=True, db_index=True
    )
    # Barcode (ISBN, UPC, GTIN, etc.) might delete this later
    barcode = models.CharField(max_length=14, null=True, blank=True, db_index=True)
    # change to blank false later

    # def clean(self):
    #     if self.has_variants:
    #         if self.sku:
    #             raise ValidationError("Products with variants should not have a SKU.")
    #         if self.price:
    #             raise ValidationError("Products with variants should not have a price.")
    #         if self.quantity:
    #             raise ValidationError(
    #                 "Products with variants should not have a quantity."
    #             )
    #     else:
    #         if not self.sku:
    #             raise ValidationError("Simple products must have a SKU.")

    # Collections are defined by you.
    # If we delete the collection model,
    collections = models.ManyToManyField(
        ProductCollection, related_name="products", blank=True
    )

    tags = ArrayField(
        models.CharField(max_length=100, blank=True, null=True),
        default=list,
        blank=True,
        null=True,
    )

    # Best to standardize with a select input like shopify.
    # classify this by processing the image file with AI
    # This is predefined and standardized accross the marketing channels like facebook etc
    # category = models.CharField(null=True, blank=True)
    # this should be mandatory later
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, blank=True, null=True, db_index=True
    )

    # What the product is counted in and how its stock is packed. Facts
    # about the product itself, so they live here once and every warehouse
    # row reads them — see marketing/units.py. (Not is_packaged/pack_count
    # below: those describe how the storefront SELLS it, "pack of 12".)
    unit = models.CharField(
        max_length=8, choices=units.UNIT_CHOICES, default=units.DEFAULT_UNIT,
        help_text="What this product is counted in",
    )
    pack_type = models.CharField(
        max_length=12, choices=units.PACK_CHOICES, default=units.DEFAULT_PACK,
        help_text="What one stock item of this product physically is",
    )

    # The storefront's coarser unit. Derived from `unit` on every save, so
    # it can't disagree with the stock again; never edit it directly.
    unit_of_measurement = models.CharField(
        choices=QUANTITY_UNIT_TYPE_CHOICES,
        null=True,
        blank=True,
        default=QUANTITY_UNIT_TYPE_CHOICES[0][0],
        editable=False,
    )

    # NO quantity column. A catalog product's stock is the sum of what the
    # warehouse physically holds for its variants, read at the moment it is
    # asked for — see `live_quantity` / with_product_live_quantity() below.
    minimum_inventory_level = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Set price of the product for online sale. (If the product has a variant this should be null maybe)
    # Never below zero (zero is a real, free item). The validator gives the
    # form a message on the field; the CheckConstraints in Meta are what hold
    # for the bulk_update and sync paths that never call full_clean().
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    # Product cost for profit calculation
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # ── Per-product OVERRIDES of the product group's defaults ──
    # Null = inherit from category; the effective_* properties below resolve
    # the fallback chain (product → category → None).
    profit_margin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text=_lz("Margin % — left blank, the product group's applies"),
    )
    minimum_order_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_lz("Minimum order quantity — left blank, the product group's applies"),
    )

    # If true, the product will be displayed on marketing channels (website etc)
    featured = models.BooleanField(default=True, blank=True, null=True, db_index=True)

    # B2B wholesale: when the product is sold as a multi-pack rather than
    # by individual unit, set is_packaged=True and put the pack size in
    # pack_count. The storefront uses these to render copy like
    # "12'li paket" / "Pack of 12" — pulled live from the API instead of
    # being hardcoded in the front-end.
    is_packaged = models.BooleanField(
        default=False,
        help_text=_lz("Is this product sold in packs? (of 12, of 5, etc.)"),
    )
    pack_count = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=_lz("How many pieces are in a pack? (required when is_packaged=True)"),
    )
    # If true, the product will be available for sale even if you have no stock.
    selling_while_out_of_stock = models.BooleanField(
        default=False, blank=True, null=True
    )
    # will be calculated for shipping quotes and optional to enter
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_of_weight = models.CharField(
        choices=WEIGHT_UNIT_TYPE_CHOICES,
        default=WEIGHT_UNIT_TYPE_CHOICES[0][0],
        blank=True,
        null=True,
    )

    # Who we buy this from — the CURRENT ACCOUNT, not a crm.Supplier. The two
    # were separate namespaces: the balances staff actually keep live on
    # accounts (most imported from KARVEN with no Supplier row), so a
    # product tagged with a Supplier pointed at a record that frequently
    # had no account behind it at all. Warehouse intake posts purchases to
    # accounts, so the product's vendor is the same account or it's a lie.
    supplier_account = models.ForeignKey(
        "accounting.CurrentAccount",
        related_name="products",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_index=True,
    )

    # supplier_lead_time = models.PositiveIntegerField(null=True, blank=True)
    # has_variants = models.BooleanField(default=False)
    datasheet_url = models.URLField(null=True, blank=True)

    # this is for displaying the product on the website's products grid.
    primary_image = models.ForeignKey(
        # quote the model name as a string to avoid circular import issues
        "ProductFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_for_products",
    )

    # The default manager hands back only what the person behind the
    # request may read (crm.models.DirectoryManager) — on the manager, as
    # for customers, because products are read from over a hundred places
    # and a wall each has to remember is a wall one will forget.
    # `everywhere` is the unwalled one: the SKU check, the catalogue
    # sync's "does this code exist at all", and data fixes.
    objects = _directory_manager()
    everywhere = models.Manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0) | models.Q(price__isnull=True),
                name="marketing_product_price_not_negative",
            ),
            models.CheckConstraint(
                check=models.Q(cost__gte=0) | models.Q(cost__isnull=True),
                name="marketing_product_cost_not_negative",
            ),
        ]

    def __str__(self):
        if self.sku:
            return self.sku
        else:
            return self.title

    def save(self, *args, **kwargs):
        if self.directory_id is None:
            from crm.models import working_directory
            self.directory = working_directory()
        self.unit_of_measurement = units.UNIT_TO_STOREFRONT.get(self.unit, "units")
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "unit" in update_fields:
            kwargs["update_fields"] = {*update_fields, "unit_of_measurement"}
        super().save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        # Settled before the fields are checked: a product validated
        # before its first save has no directory yet.
        if self.directory_id is None:
            from crm.models import working_directory
            self.directory = working_directory()
        super().clean_fields(exclude=exclude)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        # A SKU is one product's on the whole install — the storefront
        # is one catalogue — but the stock check above only looks where
        # its reader can see. Without this, a code already used by
        # another business passes validation and fails in the database.
        sku = (self.sku or "").strip()
        if sku and (exclude is None or "sku" not in exclude):
            taken = Product.everywhere.filter(sku=sku)
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            if taken.exists():
                raise ValidationError({"sku": _lz("This SKU is already in use.")})

    def share_with(self, directory):
        """Let `directory`'s people sell this product as well."""
        if directory.pk != self.directory_id:
            self.shared_with.add(directory)

    def stop_sharing_with(self, directory):
        self.shared_with.remove(directory)

    def set_unit(self, unit=None, pack_type=None):
        """Change what the product is counted in and/or how it is packed,
        keeping the storefront unit in step. Saves only what changed; returns
        whether anything did."""
        changed = []
        if unit and unit != self.unit:
            self.unit = unit
            changed.append("unit")
        if pack_type and pack_type != self.pack_type:
            self.pack_type = pack_type
            changed.append("pack_type")
        if changed:
            self.save(update_fields=changed)
        return bool(changed)

    @property
    def unit_short(self):
        return units.unit_short(self.unit)

    @property
    def item_noun(self):
        """"roll" / "box" — one stock item of this product, singular."""
        return units.pack_nouns(self.pack_type)[0]

    @property
    def item_noun_plural(self):
        return units.pack_nouns(self.pack_type)[1]

    @property
    def item_icon(self):
        return units.PACK_ICON.get(self.pack_type, "fa-layer-group")

    @property
    def counts_packs(self):
        """False for loose stock, whose page shows a quantity and no count
        of containers (units.counts_packs)."""
        return units.counts_packs(self.pack_type)

    @property
    def quantity_label(self):
        return units.quantity_label(self.unit)

    # Fallback chain: product override → product group default → None.
    @property
    def effective_profit_margin(self):
        if self.profit_margin is not None:
            return self.profit_margin
        return self.category.profit_margin if self.category_id else None

    @property
    def effective_minimum_order_quantity(self):
        if self.minimum_order_quantity is not None:
            return self.minimum_order_quantity
        return self.category.minimum_order_quantity if self.category_id else None

    @property
    def live_quantity(self):
        """This product's stock: everything the warehouse holds across all
        of its variants. None when no warehouse carries any of them — the
        product is made to order, not out of stock.

        There is no stored counterpart. For lists, annotate instead with
        with_product_live_quantity() so it costs one query rather than one
        per row.
        """
        cached = self.__dict__.get("_live_quantity")
        if cached is not None:
            return cached
        from django.db.models import Sum
        return (_warehouse_product_model().objects
                .filter(catalog_variant__product_id=self.pk)
                .aggregate(s=Sum("quantity"))["s"])

    @live_quantity.setter
    def live_quantity(self, value):
        self.__dict__["_live_quantity"] = value

    def _own_translation_text(self, lang, key):
        """A product's own per-language rich text, stored by the product form
        inside description as {"translations": {"en": {...}, "tr": {...}}}."""
        raw = (self.description or "").strip()
        if not raw.startswith("{"):
            return None
        try:
            import json as _json
            data = _json.loads(raw)
            value = (data.get("translations") or {}).get(lang, {}).get(key)
            return value or None
        except (ValueError, AttributeError):
            return None

    def get_care_instructions(self, lang="en"):
        """The product's OWN care text (from its description translations)
        wins; otherwise the product group's default for that language."""
        own = self._own_translation_text(lang, "care_instructions")
        if own:
            return own
        if not self.category_id:
            return None
        if lang == "tr":
            return self.category.care_instructions_tr
        return self.category.care_instructions

    @property
    def effective_care_instructions(self):
        return self.get_care_instructions("en")


class ProductVariant(models.Model):
    # Walled by its product — see ProductPartManager.
    objects = ProductPartManager("product")
    everywhere = models.Manager()

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        # As Product.validate_unique: a variant SKU is unique across the
        # install, and the stock check only looks where its reader sees.
        sku = (self.variant_sku or "").strip()
        if sku and (exclude is None or "variant_sku" not in exclude):
            taken = ProductVariant.everywhere.filter(variant_sku=sku)
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            if taken.exists():
                raise ValidationError({"variant_sku": _lz("This SKU is already in use.")})

    class Meta:
        verbose_name_plural = "Product Variants"
        constraints = [
            models.CheckConstraint(
                check=models.Q(variant_price__gte=0) | models.Q(variant_price__isnull=True),
                name="marketing_productvariant_price_not_negative",
            ),
            models.CheckConstraint(
                check=models.Q(variant_cost__gte=0) | models.Q(variant_cost__isnull=True),
                name="marketing_productvariant_cost_not_negative",
            ),
        ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        null=False,
        blank=False,
    )
    variant_sku = models.CharField(
        max_length=SKU_MAX_LENGTH, null=False, blank=False, db_index=True, unique=True,
    )
    # Barcode (ISBN, UPC, GTIN, etc.)
    variant_barcode = models.CharField(
        max_length=14, null=True, blank=True, db_index=True
    )

    # NO variant_quantity column either. The physical rolls are the only
    # stock authority; read `live_quantity` (or annotate a queryset with
    # with_live_quantity()). A variant with no WarehouseProduct behind it
    # has no stock to quote — it is made to order, which the storefront
    # renders from `stock_tracked` rather than from a zero.
    variant_minimum_inventory_level = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Set price of the product for online sale. Same floor as Product.price.
    variant_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    variant_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # If true, the product will be displayed on marketing channels (website etc)
    variant_featured = models.BooleanField(default=True)
    variant_datasheet_url = models.URLField(null=True, blank=True)
    product_variant_attribute_values = models.ManyToManyField(
        "ProductVariantAttributeValue", related_name="variants"
    )

    def __str__(self):
        return f"{self.product.title} - {self.variant_sku}"

    @property
    def full_name(self):
        attribute_values = self.product_variant_attribute_values.select_related("product_variant_attribute")
        values = [
            f"{v.product_variant_attribute.name.capitalize()}: {v.product_variant_attribute_value}" for v in attribute_values
        ]
        return f"{self.product.title} - {' / '.join(values)}"

    # def get_primary_image(self):
    #     primary_image = self.files.filter(is_primary=True).first()
    #     if primary_image:
    #         return primary_image.file.url
    #     return (
    #         self.files.order_by("sequence").first().file.url
    #         if self.files.exists()
    #         else None
    #     )

    # --------------
    # This is to record the attributes of the product variant and show them in the admin panel.
    def attribute_summary(self):
        # Get all attribute values for this variant
        values = self.product_variant_attribute_values.select_related("product_variant_attribute")
        return ", ".join(
            f"{v.product_variant_attribute.name}: {v.product_variant_attribute_value}"
            for v in values
        )

    attribute_summary.short_description = "Attributes"
    # --------------

    @property
    def live_quantity(self):
        """How much of this variant there actually is.

        The warehouse is the ONLY authority: a variant's stock is the SUM of
        every WarehouseProduct linked to it, so a SKU held in two depots
        reports both. A variant no warehouse carries returns None — not
        zero. The two mean different things to a buyer ("we are out of it"
        versus "we make it to order"), and callers tell them apart with
        `stock_tracked`.

        Deriving this rather than mirroring it into a column is the whole
        point. The column had five separate writers (intake, order
        deductions, CSV, the stock API, a reconciler) which is how 181 rows
        drifted out of step and 1,507 variants with no warehouse row behind
        them ended up advertising 31,533 metres that did not exist.

        One query per access — fine for a handful of variants. For lists use
        with_live_quantity() below, which resolves it in the same query and
        assigns it through the setter, so both routes read the same way.
        """
        cached = self.__dict__.get("_live_quantity")
        if cached is not None:
            return cached
        from django.db.models import Sum
        return self.warehouse_products.aggregate(s=Sum("quantity"))["s"]

    @property
    def stock_tracked(self):
        """False = no warehouse carries this variant, so there is no
        quantity to quote and it must not read as out of stock."""
        cached = self.__dict__.get("_stock_tracked")
        if cached is not None:
            return cached
        return self.warehouse_products.exists()

    @stock_tracked.setter
    def stock_tracked(self, value):
        self.__dict__["_stock_tracked"] = value

    @live_quantity.setter
    def live_quantity(self, value):
        # Django assigns annotations onto the instance; without a setter the
        # annotated queryset would raise rather than fill the property.
        self.__dict__["_live_quantity"] = value


def with_live_quantity(queryset):
    """Annotate `live_quantity` and `stock_tracked` onto a ProductVariant
    queryset — the same rule as the properties, resolved in SQL so a list
    costs one query. live_quantity stays NULL for a variant no warehouse
    carries, exactly as the property returns None."""
    from django.db.models import DecimalField, Exists, OuterRef, Subquery, Sum
    rows = _warehouse_product_model().objects.filter(catalog_variant=OuterRef("pk"))
    warehouse_total = (rows.values("catalog_variant")
                       .annotate(total=Sum("quantity"))
                       .values("total")[:1])
    return queryset.annotate(
        live_quantity=Subquery(
            warehouse_total,
            output_field=DecimalField(max_digits=14, decimal_places=2)),
        stock_tracked=Exists(rows),
    )


def with_product_live_quantity(queryset):
    """Annotate `live_quantity` onto a Product queryset: everything the
    warehouse holds across all of that product's variants. Products the
    warehouse does not carry at all annotate NULL, same rule as variants."""
    from django.db.models import DecimalField, OuterRef, Subquery, Sum
    per_product = (_warehouse_product_model().objects
                   .filter(catalog_variant__product=OuterRef("pk"))
                   .values("catalog_variant__product")
                   .annotate(total=Sum("quantity"))
                   .values("total")[:1])
    return queryset.annotate(
        live_quantity=Subquery(
            per_product,
            output_field=DecimalField(max_digits=14, decimal_places=2)),
    )


def _warehouse_product_model():
    """Imported lazily: marketing must not import operating at module load
    (operating already imports marketing)."""
    from operating.models import WarehouseProduct
    return WarehouseProduct


# ============================================================
# SUPPLIER CROSS-REFERENCE
# ============================================================
class SupplierItem(models.Model):
    """What ONE supplier calls one of our variants.

    The same fabric is bought from more than one mill, and each of them
    names it their own way: their article number on the quotation and the
    invoice, sometimes a GTIN on the carton. `Product.supplier_account` is
    a single FK and so could only ever hold the last one somebody set —
    it cannot say "we buy N1464T-PETROL from both Karven and Deneme, at
    these two prices". This table is that statement, one row per
    (supplier, variant) pair.

    Keyed on the supplier's SKU, NOT on a barcode. Most of our mills
    barcode at ROLL level: the code on the label is a serial, different on
    every roll, so it identifies a physical thing and can never say which
    PRODUCT arrived. Their article number is the stable one. A
    product-level GTIN goes in `supplier_barcode` when a supplier happens
    to have one — plenty don't. The SKU may be blank too, but only as
    "not known yet": the row then says who sells the variant and for how
    much, and waits for their code.

    Rows are written by the purchase (see marketing.supplier_items), never
    by hand as a separate chore.

    The roll serial lives on WarehouseProductItem.supplier_barcode
    instead; see that field for why the two are kept apart.
    """

    current_account = models.ForeignKey(
        "accounting.CurrentAccount",
        related_name="supplier_items",
        on_delete=models.CASCADE,
        help_text="Who sells it to us — the account the purchase is billed to",
    )
    variant = models.ForeignKey(
        ProductVariant,
        related_name="supplier_items",
        on_delete=models.CASCADE,
        help_text="What it is in OUR catalog",
    )

    # ── Their names for it ────────────────────────────────────────
    # Blank until somebody has their paper in hand: "we buy this from them,
    # at this price" is worth recording before anyone knows their code for
    # it, and every purchase made before the field existed is in that state.
    supplier_sku = models.CharField(
        max_length=SKU_MAX_LENGTH, db_index=True, blank=True, default="",
        help_text="Their article number, as printed on their invoice",
    )
    # Longer than our own 14-char barcode columns on purpose: a supplier
    # code is whatever they print, and a GS1-128 carton string carries
    # application identifiers around the GTIN rather than the bare digits.
    supplier_barcode = models.CharField(
        max_length=64, blank=True, null=True, db_index=True,
        help_text="Their PRODUCT-level barcode/GTIN, if they have one. "
                  "Not a roll serial — those go on the stock item.",
    )
    supplier_description = models.CharField(
        max_length=255, blank=True,
        help_text="How the line reads on their invoice, for reconciliation",
    )

    # ── How their unit relates to ours ────────────────────────────
    # They sell a box of 12 and we stock singles; they quote yards and we
    # hold metres. Without this every price comparison below is a lie and
    # a scanned quantity lands wrong. 1 means "same unit as ours".
    supplier_unit = models.CharField(
        max_length=20, blank=True,
        help_text="The unit they sell in (box, yard, roll…). Blank = ours.",
    )
    qty_per_supplier_unit = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="How much of OUR unit one of THEIR units is",
    )

    # ── What it last cost from them ───────────────────────────────
    # A hint for the next purchase order and the raw material of "who is
    # cheapest for this". Stamped from the purchase, never authoritative:
    # the ledger's answer is WarehouseProductItem.unit_cost_base.
    last_unit_price = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Their price per THEIR unit, when we last bought it",
    )
    # The money that price is in. A supplier is billed in their account's
    # currency, but a line can be priced in another, and a bare 1.60 says
    # nothing next to another supplier's 68.
    last_price_currency = models.CharField(max_length=4, blank=True, default="")
    last_purchased_at = models.DateField(null=True, blank=True)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_order_qty = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Which supplier we buy this from by default. Advisory — it picks the
    # row a fresh purchase order line starts from; it never stops anyone
    # buying the same variant from someone else.
    is_preferred = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier item"
        verbose_name_plural = "Supplier items"
        ordering = ["-is_preferred", "supplier_sku"]
        constraints = [
            # One supplier's article number means exactly one thing. The
            # reverse is deliberately NOT constrained: the same variant
            # may appear once per supplier, which is the whole point.
            # Only once it is known — any number of rows may still be
            # waiting for theirs.
            models.UniqueConstraint(
                fields=["current_account", "supplier_sku"],
                condition=~models.Q(supplier_sku=""),
                name="marketing_supplieritem_unique_sku_per_account",
            ),
            # Same for a product-level GTIN, when there is one. NULLs
            # repeat freely, so suppliers without barcodes are unaffected.
            models.UniqueConstraint(
                fields=["current_account", "supplier_barcode"],
                name="marketing_supplieritem_unique_barcode_per_account",
            ),
            # A variant is listed at most once per supplier — two rows
            # would make "their price for this" ambiguous.
            models.UniqueConstraint(
                fields=["current_account", "variant"],
                name="marketing_supplieritem_unique_variant_per_account",
            ),
            models.CheckConstraint(
                check=models.Q(qty_per_supplier_unit__gt=0),
                name="marketing_supplieritem_qty_per_unit_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["variant", "-is_preferred"]),
        ]

    def __str__(self):
        return f"{self.current_account} · {self.supplier_sku or '?'} → {self.variant.variant_sku}"

    def to_our_quantity(self, supplier_quantity):
        """Their quantity, restated in our unit of measure."""
        return Decimal(str(supplier_quantity)) * self.qty_per_supplier_unit


# Example: Size and Color Attributes
# Make this unique and do get or create when creating the product variant
# ============================================================
# PRODUCT ATTRIBUTES
# Descriptive attributes such as fabric type, width, length, intended use
# Hem Product'a hem de ProductVariant'a eklenebilir
# ============================================================
class ProductAttribute(models.Model):
    """
    Attributes of a product or a variant.
    Example: width: 150cm, fabric type: tulle, use: bridal
    """
    name = models.CharField(
        max_length=255, 
        verbose_name=_lz("Attribute name"),
        help_text=_lz("E.g. width, fabric type, intended use")
    )
    value = models.CharField(
        max_length=500, 
        verbose_name=_lz("Attribute value"),
        help_text=_lz("E.g. 150cm, tulle, bridal")
    )
    
    # Attached to a product or a variant (one of the two is required)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="attributes",
        null=True,
        blank=True,
        db_index=True
    )
    product_variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.CASCADE,
        related_name="attributes",
        null=True,
        blank=True,
        db_index=True
    )
    
    # For ordering
    sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sequence', 'name']
        verbose_name = "Product Attribute"
        verbose_name_plural = "Product Attributes"
        indexes = [
            models.Index(fields=['product', 'name']),
            models.Index(fields=['product_variant', 'name']),
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # One of product or variant is required (never both)
        if not self.product and not self.product_variant:
            raise ValidationError(_lz("Pick a product or a product variant."))
        if self.product and self.product_variant:
            raise ValidationError(_lz("A product and a variant can't both be picked."))
    
    def __str__(self):
        parent = self.product or self.product_variant
        return f"{self.name}: {self.value}"


# ============================================================
# VARIANT ATTRIBUTES
# The attributes that tell variants apart: colour, size, material
# ============================================================
class ProductVariantAttribute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Attribute Name", unique=True)

    def save(self, *args, **kwargs):
        # One spelling for every writer — see marketing/attributes.py. Spaces
        # stay single rather than removed: the storefront reads
        # "size per panel" by that name.
        self.name = normalize_attribute_name(self.name)
        super(ProductVariantAttribute, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariantAttributeValue(models.Model):
    class Meta:
        # A variant's attributes read the same way everywhere. Without an
        # ordering the m2m came back in whatever order Postgres happened to
        # return the through rows, so one variant showed "color / width" and
        # the next "width / color" on the same product page — a list nobody
        # can scan down. Ordering here rather than at each call site is what
        # keeps the product page, the purchase line, the catalog and
        # full_name/attribute_summary telling the same story.
        ordering = ["product_variant_attribute__name", "product_variant_attribute_value"]
        unique_together = (
            "product_variant_attribute",
            "product_variant_attribute_value",
        )
        indexes = [
            models.Index(fields=['product_variant_attribute']),  # Fast attribute lookup
        ]

    product_variant_attribute = models.ForeignKey(
        ProductVariantAttribute, on_delete=models.CASCADE, db_index=True
    )
    product_variant_attribute_value = models.CharField(
        max_length=255, verbose_name="Attribute Value", db_index=True
    )  # e.g., "S", "Red"

    def __str__(self):
        return f"{self.product_variant_attribute.name}: {self.product_variant_attribute_value}"

    def save(self, *args, **kwargs):
        # Sizes keep their spaces ("130 x 210 cm"); see marketing/attributes.py.
        self.product_variant_attribute_value = normalize_attribute_value(
            self.product_variant_attribute.name, self.product_variant_attribute_value)
        super().save(*args, **kwargs)


class VariantAttributeValueImage(models.Model):
    """Stores a single image + display name per (product, attribute_value) — used for color swatches.

    Per-product because different products may need different swatches/names for the
    same color value (e.g. velvet red vs. cotton red).
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='attribute_value_images',
    )
    attribute_value = models.ForeignKey(
        ProductVariantAttributeValue,
        on_delete=models.CASCADE,
        related_name='product_images',
    )
    # Original case-preserved display name (e.g. "Crimson Red"); the
    # canonical normalized form lives on attribute_value.product_variant_attribute_value.
    display_name = models.CharField(max_length=255, blank=True, default='')
    image_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'attribute_value')
        indexes = [
            models.Index(fields=['product', 'attribute_value']),
        ]

    def __str__(self):
        name = self.display_name or self.attribute_value.product_variant_attribute_value
        return f"{self.product.sku} / {name} → {self.image_url[-30:]}"


# class ProductVariantAttributeValue(models.Model):
#     product = models.ForeignKey(
#         Product,
#         on_delete=models.CASCADE,
#         related_name="variant_attribute_values",
#         null=False,
#         blank=False,
#     )
#     product_variant = models.ForeignKey(
#         ProductVariant,
#         on_delete=models.CASCADE,
#         related_name="attribute_values",
#         null=False,
#         blank=False,
#     )

#     product_variant_attribute = models.ForeignKey(
#         ProductVariantAttribute, on_delete=models.CASCADE
#     )
#     product_variant_attribute_value = models.CharField(
#         max_length=255, verbose_name="Attribute Value", db_index=True
#     )  # e.g., "S", "Red"

#     def __str__(self):
#         return f"{self.product_variant} |{self.product_variant_attribute.name}: {self.product_variant_attribute_value}"

#     class Meta:
#         unique_together = (
#             "product_variant",
#             "product_variant_attribute",
#         )  # A variant cannot have duplicate attribute name

import re  # regex
from urllib.parse import urlparse, urlunparse

# This is to save image files.
class ProductFile(models.Model):

    # no need for this anymore since we are not storing the file physically.
    file_path = models.CharField(max_length=500, blank=True, null=True)
    # file = models.FileField(upload_to="uploads/")  # this triggers Django file handling

    file_url = models.URLField(blank=True, null=True)

    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, related_name="files", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True,
    )

    # Walled by the product it pictures, reached directly or through a
    # variant — see ProductPartManager.
    objects = ProductPartManager("product", "product_variant__product")
    everywhere = models.Manager()

    is_primary = models.BooleanField(default=False)
    sequence = models.PositiveIntegerField(default=0)
    
    # File type to distinguish images from videos
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    # Server-generated thumbnail for video files (first frame uploaded to CDN)
    video_thumbnail = models.URLField(blank=True, null=True)


    @property
    def optimized_url(self):
        return self.file_url

    @property
    def thumbnail_url(self):
        return self.file_url

    @property
    def is_video(self):
        """Helper property to check if file is a video."""
        return self.file_type == 'video'


    def delete(self, *args, **kwargs):
        """The CDN copy goes in marketing.signals.delete_cdn_file, which also
        covers bulk and cascade deletes. skip_cdn=True keeps it (for callers
        that clean the CDN up themselves)."""
        if kwargs.pop("skip_cdn", False):
            self._skip_cdn = True
        return super().delete(*args, **kwargs)

    def __str__(self):
        # return f"{self.product or self.product_variant}"
        return f"{self.product} | {self.file_url}"


# ============================================================
# PRODUCT REVIEWS
# User ratings and comments for products
# ============================================================
from django.core.validators import MinValueValidator, MaxValueValidator

class ProductReview(models.Model):
    """
    Product reviews and ratings from authenticated users.
    Only users who have purchased the product can leave reviews.
    """
    web_client = models.ForeignKey(
        'authentication.WebClient',
        on_delete=models.CASCADE,
        related_name='product_reviews',
        help_text="The user who wrote this review"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The product being reviewed"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(
        blank=True,
        help_text="Review comment text"
    )
    is_approved = models.BooleanField(
        default=True,
        help_text="Whether the review is approved and visible"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['web_client', 'product']  # One review per user per product
        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['web_client']),
        ]
    
    def __str__(self):
        return f"{self.web_client} - {self.product.title} ({self.rating}⭐)"


class GuestProductReview(models.Model):
    """Product reviews from external/guest customers (no login required)."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='guest_reviews',
        help_text="The product being reviewed"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    hide_name = models.BooleanField(default=False, help_text="Show only initials")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False, help_text="Must be approved by admin")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Guest Product Review"
        verbose_name_plural = "Guest Product Reviews"

    def display_name(self):
        if self.hide_name:
            return f"{self.first_name[0]}.{self.last_name[0]}."
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.display_name()} - {self.product.title} ({self.rating}⭐)"


class GuestReviewImage(models.Model):
    """Images attached to guest reviews."""
    review = models.ForeignKey(
        GuestProductReview,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for review #{self.review.id}"


# ============================================================
# DISCOUNT CODES
# Promo codes given to influencers / newsletter subscribers
# ============================================================
class DiscountCode(models.Model):
    """Promo codes (e.g. influencer codes, newsletter signup rewards)."""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code",
        help_text="Unique promo code (e.g. KARVEN10)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Discount Percentage",
        help_text="Discount as a percent (e.g. 10.00 for 10%)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether the code can currently be redeemed"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Usage Count",
        help_text="Number of successful orders that used this code"
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        verbose_name="Max Uses",
        help_text="0 = unlimited, 1 = single-use"
    )
    influencer_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Influencer Name",
        help_text="Optional — name of the influencer using this code"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Discount Code"
        verbose_name_plural = "Discount Codes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"

    def is_valid(self):
        """Check if code is active and under usage limit"""
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.usage_count >= self.max_uses:
            return False
        return True


# ============================================================
# NEWSLETTER SUBSCRIPTIONS
# Email + phone subscribers (newsletter / discount code signups)
# ============================================================
class NewsletterSubscription(models.Model):
    """Newsletter subscribers — uniquely identified by email and phone."""
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Subscriber email address"
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Phone",
        help_text="Subscriber phone number"
    )
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name="Discount Code"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Newsletter Subscription"
        verbose_name_plural = "Newsletter Subscriptions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.phone}"


# ============================================================
# BLOG POSTS
# Blog posts, in several languages
# ============================================================
class BlogPost(models.Model):
    """Blog post with multilingual support"""
    
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly identifier")
    
    # Multilingual Title
    title_en = models.CharField(max_length=300, verbose_name="Title (EN)")
    title_tr = models.CharField(max_length=300, blank=True, verbose_name=_lz("Title (TR)"))
    title_ru = models.CharField(max_length=300, blank=True, verbose_name="Заголовок (RU)")
    title_pl = models.CharField(max_length=300, blank=True, verbose_name="Tytuł (PL)")
    
    # Multilingual Excerpt (short description for list view)
    excerpt_en = models.TextField(verbose_name="Excerpt (EN)")
    excerpt_tr = models.TextField(blank=True, verbose_name=_lz("Excerpt (TR)"))
    excerpt_ru = models.TextField(blank=True, verbose_name="Краткое описание (RU)")
    excerpt_pl = models.TextField(blank=True, verbose_name="Streszczenie (PL)")
    
    # Multilingual Content (Markdown format)
    content_en = models.TextField(verbose_name="Content (EN)")
    content_tr = models.TextField(blank=True, verbose_name=_lz("Content (TR)"))
    content_ru = models.TextField(blank=True, verbose_name="Содержание (RU)")
    content_pl = models.TextField(blank=True, verbose_name="Treść (PL)")
    
    # Multilingual Category
    category_en = models.CharField(max_length=100, verbose_name="Category (EN)")
    category_tr = models.CharField(max_length=100, blank=True, verbose_name=_lz("Category (TR)"))
    category_ru = models.CharField(max_length=100, blank=True, verbose_name="Категория (RU)")
    category_pl = models.CharField(max_length=100, blank=True, verbose_name="Kategoria (PL)")
    
    # Images (Bunny CDN URLs)
    cover_image = models.URLField(blank=True, verbose_name=_lz("Cover image (list)"))
    hero_image = models.URLField(blank=True, verbose_name=_lz("Hero image (detail)"))
    
    # Custom Code Injection
    header_content = models.TextField(blank=True, verbose_name="Extra Header Content (CSS/Meta)", help_text="e.g. &lt;style&gt;...&lt;/style&gt; or &lt;link&gt;")
    footer_content = models.TextField(blank=True, verbose_name="Extra Footer Content (JS)", help_text="e.g. &lt;script&gt;...&lt;/script&gt;")
    
    # Meta
    author = models.CharField(max_length=200, default='Karven Home Collection')
    published_at = models.DateField(verbose_name=_lz("Publication date"))
    is_published = models.BooleanField(default=False, verbose_name=_lz("Published?"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
    
    def __str__(self):
        return self.title_en or self.title_tr or self.slug

    # Only the _en fields are required, so a post may carry any subset of
    # the four translations. These read the active language and fall back
    # through the rest rather than showing an admin page a blank title.
    LANGUAGES = ("en", "tr", "ru", "pl")

    def localized(self, field):
        """`field` in the active language, else the first one filled in."""
        from django.utils.translation import get_language

        active = (get_language() or "en").lower().split("-")[0]
        for code in (active, *self.LANGUAGES):
            value = getattr(self, f"{field}_{code}", "")
            if value:
                return value
        return ""

    @property
    def title(self):
        return self.localized("title") or self.slug

    @property
    def excerpt(self):
        return self.localized("excerpt")

    @property
    def category(self):
        return self.localized("category")

    def delete(self, *args, **kwargs):
        """Delete cover and hero images from CDN when deleting the post"""
        from .views import smart_delete
        for image_url in [self.cover_image, self.hero_image]:
            if image_url:
                try:
                    smart_delete(image_url)
                except Exception as e:
                    print(f"Failed to delete CDN resource {image_url}: {e}")
        super().delete(*args, **kwargs)


class BlogFile(models.Model):
    """Blog post images"""
    
    blog_post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='files',
        null=False,
        blank=False
    )
    
    file_url = models.URLField(blank=True, null=True)

    # File type: 'cover', 'hero', 'content'
    FILE_TYPE_CHOICES = [
        ('cover', _lz("Cover image")),
        ('hero', _lz("Hero image")),
        ('content', _lz("Content image")),
    ]
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='content'
    )
    
    # Alt text for accessibility
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    
    sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sequence', 'pk']
        verbose_name = _lz("Blog file")
        verbose_name_plural = _lz("Blog files")
    
    def delete(self, *args, **kwargs):
        """Delete from CDN when deleting the record"""
        if self.file_url:
            try:
                from .views import smart_delete
                smart_delete(self.file_url)
            except Exception as e:
                print(f"Failed to delete CDN resource {self.file_url}: {e}")
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.blog_post.title_tr} - {self.file_type}"


# ============================================================
# PRODUCT CAMPAIGNS / DISCOUNTS
# A product takes one kind of campaign:
#   - 'percentage' : a fixed percentage discount + an end date
#   - 'volume'     : a tiered discount by quantity
# ============================================================
class ProductCampaign(models.Model):
    TYPE_CHOICES = [
        ('percentage', 'Percentage Discount'),
        ('volume',     'Volume / Quantity Tier'),
    ]
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='campaign',
    )
    campaign_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    # Used only when campaign_type == 'percentage'
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Used only for percentage campaigns. Example: 15.00 = %15'
    )
    end_date = models.DateField(
        null=True, blank=True,
        help_text='When the percentage discount expires (inclusive).'
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Campaign({self.product.title}, {self.campaign_type})'


class ProductCampaignTier(models.Model):
    '''A single bracket in a volume campaign:
       e.g. 0–1000 units → %5 off.'''
    campaign = models.ForeignKey(
        ProductCampaign,
        on_delete=models.CASCADE,
        related_name='tiers',
    )
    min_qty = models.PositiveIntegerField()
    max_qty = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Leave blank for an open-ended top tier (7500+).'
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['min_qty']

    def __str__(self):
        cap = self.max_qty if self.max_qty else '+'
        return f'{self.min_qty}–{cap} → %{self.discount_percent}'


# ---------------------------------------------------------------------------
# Mail system — moved here from the old `email_automation` app. The models
# live in models_email.py to keep this module readable; they are re-exported
# so `marketing.models.Email` and friends resolve the way every other
# marketing model does.
# ---------------------------------------------------------------------------
from .models_email import (  # noqa: E402,F401
    EmailAccount,
    EmailTemplate,
    EmailCampaign,
    SentEmail,
    ReceivedEmail,
    Email,
    EmailAttachment,
)

# Quotes — see models_quotes.py; re-exported so marketing.models.Quote resolves.
from .models_quotes import Quote, QuoteItem, QuoteItemRoll  # noqa: E402,F401
