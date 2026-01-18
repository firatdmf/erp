from django.db import models
import os
import time

# Standardized labels used to identify the nature and format of a file's content
import mimetypes
from django.core.exceptions import ValidationError
from crm.models import Supplier
from django.contrib.postgres.fields import ArrayField

# cdn for media
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.utils import cloudinary_url
from cloudinary.exceptions import Error as CloudinaryError


# Create your functions here.
# --------------------------------------------------------------------------------------------
# FILE SAVER FUNCTION FOR THE PRODUCTS


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
    class Meta:
        verbose_name_plural = "Product Categories"

    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    description = models.TextField(null=True, blank=True)

    image_url = models.URLField(null=True, blank=True)  # Store Cloudinary URL

    def save(self, *args, **kwargs):

        self.name = self.name.lower().strip().replace(" ", "_")
        # _image_file is a temporary attribute (not a model field) used to hold the uploaded file just long enough to upload it to Cloudinary in the save() method.
        image_file = getattr(self, "_image_file", None)
        # When you upload an image via a form, the file comes in as a file object (not a URL).
        # You need to upload this file to Cloudinary, get the resulting URL, and then store that URL in the image field.
        if image_file:
            try:
                # Set folder and public_id for Cloudinary
                folder = f"media/product_categories/{self.name}"
                public_id = os.path.splitext(image_file.name)[
                    0
                ]  # filename without extension
                result = cloudinary_upload(
                    image_file,
                    folder=folder,
                    public_id=public_id,
                    overwrite=True,  # Overwrite if same name
                    resource_type="image",
                )
                self.image_url = result.get("secure_url")
            except CloudinaryError as e:
                raise ValidationError(f"Cloudinary upload failed: {e}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    created_at = models.DateTimeField(auto_now=True, blank=False, null=False)
    QUANTITY_UNIT_TYPE_CHOICES = [
        ("units", "Unit"),
        ("mt", "Meter"),
        ("kg", "Kilogram"),
    ]
    WEIGHT_UNIT_TYPE_CHOICES = [("lb", "lb"), ("oz", "oz"), ("kg", "kg"), ("g", "g")]

    title = models.CharField(max_length=255, null=False, blank=False)

    # This can be implement and used as html later.
    description = models.TextField(null=True, blank=True)

    # Stock Keeping Unit
    # This should be unique also
    # If the product has a variant, this should be null
    sku = models.CharField(
        max_length=20, null=True, blank=False, unique=True, db_index=True
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
    # Product cost for profit calculation
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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

    def __str__(self):
        if self.sku:
            return self.sku
        else:
            return self.title


class ProductVariant(models.Model):
    class Meta:
        verbose_name_plural = "Product Variants"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        null=False,
        blank=False,
    )
    variant_sku = models.CharField(
        max_length=20, null=False, blank=False, db_index=True
    )
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


# Example: Size and Color Attributes
# Make this unique and do get or create when creating the product variant
# ============================================================
# PRODUCT ATTRIBUTES (Ürün Özellikleri)
# Kumaş türü, en, boy, kullanım alanı gibi özellikler
# Hem Product'a hem de ProductVariant'a eklenebilir
# ============================================================
class ProductAttribute(models.Model):
    """
    Product veya Variant özellikleri
    Örnek: En: 150cm, Kumaş Türü: Tül, Kullanım: Gelinlik
    """
    name = models.CharField(
        max_length=255, 
        verbose_name="Özellik Adı",
        help_text="Örn: En, Kumaş Türü, Kullanım Alanı"
    )
    value = models.CharField(
        max_length=500, 
        verbose_name="Özellik Değeri",
        help_text="Örn: 150cm, Tül, Gelinlik"
    )
    
    # Product veya Variant'a bağlanır (ikisinden biri zorunlu)
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
    
    # Sıralama için
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
        # Product veya Variant'tan biri zorunlu (ikisi birden olamaz)
        if not self.product and not self.product_variant:
            raise ValidationError("Product veya Product Variant seçilmeli.")
        if self.product and self.product_variant:
            raise ValidationError("Product ve Variant aynı anda seçilemez.")
    
    def __str__(self):
        parent = self.product or self.product_variant
        return f"{self.name}: {self.value}"


# ============================================================
# VARIANT ATTRIBUTES (Variant Ayırıcılar)
# Color, Size, Material gibi variant'ları ayıran özellikler
# ============================================================
class ProductVariantAttribute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Attribute Name", unique=True)

    def save(self, *args, **kwargs):
        # Convert the name to lowercase before saving
        self.name = self.name.lower().replace(" ", "")
        super(ProductVariantAttribute, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariantAttributeValue(models.Model):
    class Meta:
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
    # code = models.CharField(max_length=255, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.product_variant_attribute.name}: {self.product_variant_attribute_value}"

    def save(self, *args, **kwargs):
        self.product_variant_attribute_value = (
            self.product_variant_attribute_value.lower().replace(" ", "_")
        )
        # if not self.code:
        #     attr_code = str(self.product_variant_attribute.pk)
        #     value_code = (
        #         self.product_variant_attribute_value.strip().upper().replace(" ", "_")
        #     )
        #     self.code = f"{attr_code}_{value_code}"
        super().save(*args, **kwargs)


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
from cloudinary.uploader import destroy as cloudinary_destroy
from urllib.parse import urlparse, urlunparse

# This is to save image files.
class ProductFile(models.Model):

    # no need for this anymore since we are not storing the file physically.
    file_path = models.CharField(max_length=500, blank=True, null=True)
    # file = models.FileField(upload_to="uploads/")  # this triggers Django file handling

    # this is the cloudinary url
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

    is_primary = models.BooleanField(default=False)
    sequence = models.PositiveIntegerField(default=0)
    
    # File type to distinguish images from videos
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')


    @property
    def optimized_url(self):
        """
        Returns the Cloudinary URL with automatic format and quality.
        Example: https://res.cloudinary.com/.../upload/f_auto,q_auto/.../file.png
        """
        if not self.file_url:
            return None

        parts = urlparse(self.file_url)
        # Insert transformations right after /upload/
        optimized_path = parts.path.replace("/upload/", "/upload/f_auto,q_auto/")
        return urlunparse(parts._replace(path=optimized_path))
    
    @property
    def thumbnail_url(self):
        """
        Returns optimized thumbnail URL for list views (80x80, low quality).
        Drastically reduces file size: 300KB → ~5KB!
        """
        if not self.file_url:
            return None
        
        parts = urlparse(self.file_url)
        # Aggressive optimization for list view thumbnails
        optimized_path = parts.path.replace(
            "/upload/", 
            "/upload/w_80,h_80,c_fill,f_auto,q_auto:low/"
        )
        return urlunparse(parts._replace(path=optimized_path))
    
    @property
    def video_thumbnail_url(self):
        """
        Returns thumbnail URL for video files (first frame).
        Uses Cloudinary's video-to-image transformation.
        """
        if not self.file_url or self.file_type != 'video':
            return None
        
        parts = urlparse(self.file_url)
        # Convert video to image thumbnail (jpg from first frame)
        # w_300 = width, h_200 = height, c_fill = crop to fill, so_0 = start offset 0 (first frame)
        optimized_path = parts.path.replace(
            "/upload/", 
            "/upload/w_300,h_200,c_fill,so_0,f_jpg/"
        )
        # Change extension to .jpg for the thumbnail
        if optimized_path.endswith(('.mp4', '.mov', '.webm', '.avi')):
            optimized_path = optimized_path.rsplit('.', 1)[0] + '.jpg'
        return urlunparse(parts._replace(path=optimized_path))
    
    @property
    def is_video(self):
        """Helper property to check if file is a video."""
        return self.file_type == 'video'


    # only works on single delete, not bulk delete. For bulk we use signals.py
    def delete(self, *args, **kwargs):
        start = time.perf_counter()
        print(f"🗑️ ProductFile.delete(pk={self.pk}) called")
        """
        Extracts public_id from a Cloudinary URL and deletes it.
        SKIP Cloudinary deletion if skip_cloudinary=True (for async cleanup).
        """
        skip_cloudinary = kwargs.pop('skip_cloudinary', False)
        
        if self.file_url and not skip_cloudinary:
            match = re.search(r"/upload/(?:v\d+/)?([^\.]+)", self.file_url)
            if match:
                public_id = match.group(1)  # e.g. "media/product_images/sku123/file1"
                try:
                    c_start = time.perf_counter()
                    cloudinary_destroy(public_id)
                    print(f"   ✅ Cloudinary destroy({public_id}) took {(time.perf_counter()-c_start):.3f}s")
                except Exception as e:
                    print(f"   ❌ Failed to delete Cloudinary resource {public_id}: {e}")
            else:
                print("   ⚠️ Could not extract public_id from URL")
        elif skip_cloudinary:
            print(f"   ⚡ Skipped Cloudinary deletion for pk={self.pk} (will be cleaned up async)")

        # finally delete the DB record
        db_start = time.perf_counter()
        super().delete(*args, **kwargs)
        print(f"   🗃️ DB delete took {(time.perf_counter()-db_start):.3f}s | TOTAL {(time.perf_counter()-start):.3f}s")

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


# ============================================================
# DISCOUNT CODES
# İndirim kodları - fenomenler için
# ============================================================
class DiscountCode(models.Model):
    """İndirim kodları - influencerlara verilecek kodlar"""
    code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="İndirim Kodu",
        help_text="Fenomene verilecek benzersiz kod (örn: KARVEN10)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="İndirim Yüzdesi",
        help_text="Yüzde olarak indirim miktarı (örn: 10.00 için %10)"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Aktif",
        help_text="Kod aktif mi?"
    )
    usage_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="Kullanım Sayısı",
        help_text="Bu kodla kaç başarılı sipariş oluşturuldu"
    )
    influencer_name = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Fenomen Adı",
        help_text="Bu kodu kullanacak fenomenin adı (opsiyonel)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "İndirim Kodu"
        verbose_name_plural = "İndirim Kodları"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"


# ============================================================
# BLOG POSTS
# Blog yazıları - çok dilli destek ile
# ============================================================
class BlogPost(models.Model):
    """Blog post with multilingual support"""
    
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly identifier")
    
    # Multilingual Title
    title_tr = models.CharField(max_length=300, verbose_name="Başlık (TR)")
    title_en = models.CharField(max_length=300, blank=True, verbose_name="Title (EN)")
    title_ru = models.CharField(max_length=300, blank=True, verbose_name="Заголовок (RU)")
    title_pl = models.CharField(max_length=300, blank=True, verbose_name="Tytuł (PL)")
    
    # Multilingual Excerpt (short description for list view)
    excerpt_tr = models.TextField(verbose_name="Özet (TR)")
    excerpt_en = models.TextField(blank=True, verbose_name="Excerpt (EN)")
    excerpt_ru = models.TextField(blank=True, verbose_name="Краткое описание (RU)")
    excerpt_pl = models.TextField(blank=True, verbose_name="Streszczenie (PL)")
    
    # Multilingual Content (Markdown format)
    content_tr = models.TextField(verbose_name="İçerik (TR)")
    content_en = models.TextField(blank=True, verbose_name="Content (EN)")
    content_ru = models.TextField(blank=True, verbose_name="Содержание (RU)")
    content_pl = models.TextField(blank=True, verbose_name="Treść (PL)")
    
    # Multilingual Category
    category_tr = models.CharField(max_length=100, verbose_name="Kategori (TR)")
    category_en = models.CharField(max_length=100, blank=True, verbose_name="Category (EN)")
    category_ru = models.CharField(max_length=100, blank=True, verbose_name="Категория (RU)")
    category_pl = models.CharField(max_length=100, blank=True, verbose_name="Kategoria (PL)")
    
    # Images (Cloudinary URLs)
    cover_image = models.URLField(blank=True, verbose_name="Kapak Resmi (Liste)")
    hero_image = models.URLField(blank=True, verbose_name="Hero Resmi (Detay)")
    
    # Meta
    author = models.CharField(max_length=200, default='Karven Home Collection')
    published_at = models.DateField(verbose_name="Yayın Tarihi")
    is_published = models.BooleanField(default=False, verbose_name="Yayında mı?")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = "Blog Yazısı"
        verbose_name_plural = "Blog Yazıları"
    
    def __str__(self):
        return self.title_tr
    
    def delete(self, *args, **kwargs):
        """Delete cover and hero images from Cloudinary when deleting the post"""
        for image_url in [self.cover_image, self.hero_image]:
            if image_url and 'cloudinary.com' in image_url:
                match = re.search(r"/upload/(?:v\d+/)?([^\.]+)", image_url)
                if match:
                    public_id = match.group(1)
                    try:
                        cloudinary_destroy(public_id)
                    except Exception as e:
                        print(f"Failed to delete Cloudinary resource {public_id}: {e}")
        super().delete(*args, **kwargs)


class BlogFile(models.Model):
    """Blog post images - stored on Cloudinary"""
    
    blog_post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='files',
        null=False,
        blank=False
    )
    
    # Cloudinary URL
    file_url = models.URLField(blank=True, null=True)
    
    # File type: 'cover', 'hero', 'content'
    FILE_TYPE_CHOICES = [
        ('cover', 'Kapak Resmi'),
        ('hero', 'Hero Resmi'),
        ('content', 'İçerik Resmi'),
    ]
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='content'
    )
    
    # Alt text for accessibility
    alt_text = models.CharField(max_length=255, blank=True)
    
    sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sequence', 'pk']
        verbose_name = "Blog Dosyası"
        verbose_name_plural = "Blog Dosyaları"
    
    def delete(self, *args, **kwargs):
        """Delete from Cloudinary when deleting the record"""
        if self.file_url:
            match = re.search(r"/upload/(?:v\d+/)?([^\.]+)", self.file_url)
            if match:
                public_id = match.group(1)
                try:
                    cloudinary_destroy(public_id)
                except Exception as e:
                    print(f"Failed to delete Cloudinary resource {public_id}: {e}")
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.blog_post.title_tr} - {self.file_type}"
