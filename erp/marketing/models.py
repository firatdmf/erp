from django.db import models

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
def product_variants_default():
    return {
        "variants": {
            "color": "champange",
            "size": "84",
        }
    }


# --------------------------------------------------------------------------------------------
# FILE SAVER FUNCTION FOR THE PRODUCTS
def product_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/products/<product_id>/<filename>
    return f"marketing/static/media/products/{instance.id}_{instance.sku}/{filename}"


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
        "video/mp4",
        "video/hls",
        "audio/mpeg",
    ]
    mime_type, encoding = mimetypes.guess_type(file.name)
    if mime_type not in valid_mime_types:
        raise ValidationError(
            "Unsupported file type. Allowed types are: jpg, png, gif, webp, mp4, hls, mp3."
        )
    return file


def validate_image_type(image):
    valid_mime_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    mime_type, encoding = mimetypes.guess_type(image.name)
    if mime_type not in valid_mime_types:
        raise ValidationError(
            "Unsupported file type. Allowed types are: jpg, png, gif, webp, mp4, hls, mp3."
        )
    return image


# ---------------------------------------------------------------------------------------------

# Create your models here.


class ProductCollection(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.FileField(
        upload_to=product_directory_path,
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
    # change to blank false later, if product has variants, no sku should be set to null.
    # This should be unique also
    sku = models.CharField(max_length=12, null=True, blank=True)
    # Barcode (ISBN, UPC, GTIN, etc.)
    barcode = models.CharField(max_length=14, null=True, blank=True)
    # change to blank false later

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
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, blank=True, null=True
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
    # Set price of the product for online sale. (If the product has a variant this should be null maybe)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # If true, the product will be displayed on marketing channels (website etc)
    featured = models.BooleanField(default=True, blank=True, null=True)
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
    )
    # supplier = models.CharField( null=True, blank=True)

    def __str__(self):
        return self.sku


class ProductVariant(models.Model):
    class Meta:
        verbose_name_plural = "Product Variants"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        null=True,
        blank=True,
    )
    variant_sku = models.CharField(max_length=12, null=True, blank=True)
    # Barcode (ISBN, UPC, GTIN, etc.)
    variant_barcode = models.CharField(max_length=14, null=True, blank=True)

    variant_quantity = models.DecimalField(
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

    def __str__(self):
        return f"{self.product.title} - {self.variant_sku}"


# Example: Size and Color Attributes
class ProductVariantAttribute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Attribute Name")

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
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="attribute_values",
        null=True,
        blank=True,
    )

    attribute = models.ForeignKey(ProductVariantAttribute, on_delete=models.CASCADE)
    value = models.CharField(
        max_length=255, verbose_name="Attribute Value"
    )  # e.g., "S", "Red"

    def __str__(self):
        return f"{self.variant} |{self.attribute.name}: {self.value}"

    class Meta:
        unique_together = (
            "variant",
            "attribute",
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
        upload_to="product_files/",
        validators=[validate_file_size, validate_file_type],
    )
    # This is the sequence of the files
    sequence = models.SmallIntegerField(unique=True)

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set sequence if this is a new object
            last_sequence = (
                ProductFile.objects.filter(product=self.product)
                .order_by("sequence")
                .last()
            )
            if last_sequence:
                self.sequence = last_sequence.sequence + 1
            else:
                self.sequence = 1
        super(ProductFile, self).save(*args, **kwargs)

    def __str__(self):
        return f"Media for {self.product.title}"
