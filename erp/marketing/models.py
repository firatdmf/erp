from django.db import models
import os

# Standardized labels used to identify the nature and format of a file's content
import mimetypes
from django.core.exceptions import ValidationError
from crm.models import Supplier
from django.contrib.postgres.fields import ArrayField

# Create your functions here.


# def product_variants_default():
#     return {
#         "variants": {
#             "color": ["blue", "red", "green"],
#             "size": ['84"', '95"'],
#         }
#     }


# This is not used anywhere, just for the reference.
def product_variants_default():
    return {
        "variants": {
            "color": "champange",
            "size": "84",
        }
    }


# --------------------------------------------------------------------------------------------
# FILE SAVER FUNCTION FOR THE PRODUCTS
# def product_directory_path(instance, filename):
#     # file will be uploaded to MEDIA_ROOT/products/<product_id>/<filename>
#     return f"marketing/static/media/products/{instance.id}_{instance.sku}/{filename}"


def product_file_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/product_files/<product_sku>/<filename>
    # if(instance.product_variant):
    #     return f"product_files/{instance.product.sku}/{instance.product_variant.variant_sku}/{instance.sequence}_{filename}"
    # return f"product_files/{instance.product.sku}/{instance.sequence}_{filename}"
    if instance.product_variant:
        return f"product_files/{instance.product.sku}/images/productSKU_{instance.product.sku}_variantSKU_{instance.product_variant.variant_sku}_{filename}"
    else:
        return f"product_files/{instance.product.sku}/images/{filename}"


def product_category_directory_path(instance, filename):
    return f"product_categories/{instance.name}/{filename}"


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
    class Meta:
        verbose_name_plural = "Product Categories"

    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    image = models.FileField(
        upload_to=product_category_directory_path,
        null=True,
        blank=True,
        validators=[validate_file_size, validate_image_type],
    )

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    created_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    QUANTITY_UNIT_TYPE_CHOICES = [
        ("units", "Unit"),
        ("mt", "Meter"),
        ("kg", "Kilogram"),
    ]
    WEIGHT_UNIT_TYPE_CHOICES = [("lb", "lb"), ("oz", "oz"), ("kg", "kg"), ("g", "g")]

    # change to blank false later
    title = models.CharField(max_length=255, null=False, blank=False)

    # This can be implement and used as html later.
    description = models.TextField(null=True, blank=True)

    # Stock Keeping Unit
    # This should be unique also
    # If the product has a variant, this should be null
    sku = models.CharField(
        max_length=12, null=True, blank=True, unique=True, db_index=True
    )
    # Barcode (ISBN, UPC, GTIN, etc.)
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

    # This just like category but custom, you may set it to anything you like. A product can only have one type.
    type = models.CharField(null=True, blank=True)

    unit_of_measurement = models.CharField(
        choices=QUANTITY_UNIT_TYPE_CHOICES,
        null=True,
        blank=True,
        default=QUANTITY_UNIT_TYPE_CHOICES[0],
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    minimum_inventory_level = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Set price of the product for online sale. (If the product has a variant this should be null maybe)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # you may remove belows later
    # cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # If true, the product will be displayed on marketing channels (website etc)
    featured = models.BooleanField(default=True, blank=True, null=True, db_index=True)
    # If true, the product will be available for sale even if you have no stock.
    selling_while_out_of_stock = models.BooleanField(
        default=False, blank=True, null=True
    )
    # will be calculated for shipping quotes and optional to enter
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_of_weight = models.CharField(
        choices=WEIGHT_UNIT_TYPE_CHOICES,
        default=WEIGHT_UNIT_TYPE_CHOICES[0],
        blank=True,
        null=True,
    )

    supplier = models.ForeignKey(
        Supplier,
        related_name="products",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_index=True,
    )
    # supplier = models.CharField( null=True, blank=True)
    # has_variants = models.BooleanField(default=False)
    datasheet_url = models.URLField(null=True, blank=True)

    def __str__(self):
        if self.sku:
            return self.sku
        else:
            return self.title

    # def save(self, *args, **kwargs):
    #     # Convert the title to lowercase before saving
    #     super(Product, self).save(
    #         *args, **kwargs
    #     )  # Save first to ensure self.pk exists
    #     if not self.variants.exists():
    #         if self.has_variants:
    #             self.has_variants = False
    #             super().save(update_fields=["has_variants"])


class ProductVariant(models.Model):

    # def clean(self):
    #     if self.product and not self.product.has_variants:
    #         raise ValidationError(
    #             "Variants can only be associated with products that have variants."
    #         )

    class Meta:
        verbose_name_plural = "Product Variants"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        null=True,
        blank=True,
    )
    variant_sku = models.CharField(max_length=12, null=True, blank=True, db_index=True)
    # Barcode (ISBN, UPC, GTIN, etc.)
    variant_barcode = models.CharField(
        max_length=14, null=True, blank=True, db_index=True
    )

    variant_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    variant_minimum_inventory_level = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Set price of the product for online sale.
    variant_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    variant_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # If true, the product will be displayed on marketing channels (website etc)
    variant_featured = models.BooleanField(default=True)
    variant_datasheet_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.title} - {self.variant_sku}"

    @property
    def full_name(self):
        attribute_values = self.attribute_values.select_related("attribute")
        values = [
            f"{v.attribute.name.capitalize()}: {v.value}" for v in attribute_values
        ]
        return f"{self.product.title} - {' / '.join(values)}"


# Example: Size and Color Attributes
# Make this unique and do get or create when creating the product variant
class ProductVariantAttribute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Attribute Name")

    def save(self, *args, **kwargs):
        # Convert the name to lowercase before saving
        self.name = self.name.lower()
        super(ProductVariantAttribute, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariantAttributeValue(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variant_attribute_values",
        null=True,
        blank=True,
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="attribute_values",
        null=True,
        blank=True,
    )

    product_variant_attribute = models.ForeignKey(
        ProductVariantAttribute, on_delete=models.CASCADE
    )
    product_variant_attribute_value = models.CharField(
        max_length=255, verbose_name="Attribute Value", db_index=True
    )  # e.g., "S", "Red"

    def __str__(self):
        return f"{self.product_variant} |{self.product_variant_attribute.name}: {self.product_variant_attribute_value}"

    class Meta:
        unique_together = (
            "product_variant",
            "product_variant_attribute",
        )  # A variant cannot have duplicate attribute name


class ProductFile(models.Model):
    # This way I could just say product.files and get the file docs
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="files", null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True,
    )
    file = models.FileField(
        # upload_to=product_directory_path,
        upload_to=product_file_directory_path,
        validators=[validate_file_size, validate_file_type],
    )
    # This is the sequence of the files
    # sequence = models.SmallIntegerField(unique=True)

    # If the file alredy exists, delete the old file and save the new one
    def save(self, *args, **kwargs):
        # Check if the instance already exists in the database
        if self.pk:
            old_instance = ProductFile.objects.get(pk=self.pk)
            # If a new file is uploaded, delete the old file
            if old_instance.file and old_instance.file != self.file:
                if os.path.isfile(old_instance.file.path):
                    os.remove(old_instance.file.path)
        super(ProductFile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the file from the filesystem
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super(ProductFile, self).delete(*args, **kwargs)

    # below is needed to delete the files in bulk
    @classmethod
    def bulk_delete_with_files(cls, queryset):
        """
        Deletes all ProductFile instances in the queryset,
        ensuring files are removed from the filesystem.
        """
        for obj in queryset:
            obj.delete()

    def __str__(self):
        return f"Media for {self.product.sku} | {self.product.title}"

        # def save(self, *args, **kwargs):

    #     if not self.pk:  # Only set sequence if this is a new object
    #         last_sequence = (
    #             ProductFile.objects.filter(product=self.product)
    #             .order_by("sequence")
    #             .last()
    #         )
    #         if last_sequence:
    #             self.sequence = last_sequence.sequence + 1
    #         else:
    #             self.sequence = 1
    #     super(ProductFile, self).save(*args, **kwargs)
