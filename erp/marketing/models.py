from django.db import models
import mimetypes
from django.core.exceptions import ValidationError
from crm.models import Supplier
from django.contrib.postgres.fields import ArrayField
# Create your functions here.


def product_variants_default():
    return {
        "variants": {
            "color": ["blue", "red", "green"],
            "size": ['84"', '95"'],
        }
    }


# --------------------------------------------------------------------------------------------
# FILE SAVER FUNCTION FOR THE PRODUCTS
def product_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/products/<product_id>/<filename>
    return f"products/{instance.id}_{instance.sku}/{filename}"


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


class Collection(models.Model):
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
        return(f"{self.title}")


class Product(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    UNIT_TYPE_CHOICES = [("units", "Unit"), ("mt", "Meter"), ("kg", "Kilogram")]
    # Stock Keeping Unit
    # change to blank false later
    sku = models.CharField(max_length=12, null=True, blank=True)
    # Barcode (ISBN, UPC, GTIN, etc.)
    # change to blank false later
    barcode = models.CharField(max_length=14, null=True, blank=True)
    # change to blank false later
    title = models.CharField(max_length=255, null=True, blank=True)

    # This can be implement and used as html later.
    description = models.TextField(null=True, blank=True)

    media = models.FileField(
        upload_to=product_directory_path,
        null=True,
        blank=True,
        validators=[validate_file_size, validate_file_type],
    )  # Field to store files

    # Collections are defined by you.
    # If we delete the collection model,
    collections = models.ManyToManyField(
        Collection, related_name='products', blank=True
    )

    tags = ArrayField(
        models.CharField(max_length=100, blank=False),
        default=list,
        blank=True,
    )

    # Best to standardize with a select input like shopify.
    # classify this by processing the image file with AI
    # This is predefined and standardized accross the marketing channels like facebook etc
    category = models.CharField(null=True, blank=True, default="uncategorized")

    # This just like category but custom, you may set it to anything you like. A product can only have one type.
    type = models.CharField(null=True, blank=True)

    unit_of_measurement = models.CharField(
        choices=UNIT_TYPE_CHOICES, null=True, blank=True, default=UNIT_TYPE_CHOICES[0]
    )

    # Set price of the product for online sale.
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # If true, the product will be displayed on marketing channels (website etc)
    featured = models.BooleanField(default=True)
    # If true, the product will be available for sale even if you have no stock.
    selling_while_out_of_stock = models.BooleanField(default=False)

    # will be calculated for shipping quotes and optional to enter
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    variants = models.JSONField(null=True, blank=True,default=product_variants_default)

    vendor = models.ManyToManyField(Supplier,related_name="products",blank=True)

    def __str__(self):
        return self.title
