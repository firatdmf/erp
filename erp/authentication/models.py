from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
ACCESS_LEVEL_CHOICES_DICT = {
    "admin": ("Admin", "Has full access to all resources and settings."),
    "manager": (
        "Manager",
        "Can manage teams and projects, but has limited access to settings.",
    ),
    "employee": ("Employee", "Can access and manage their own tasks and projects."),
    "guest": ("Guest", "Has limited access to view certain resources."),
}

# Convert dictionary to list of tuples for name choices
ACCESS_LEVEL_NAME_CHOICES = [
    (key, value[0]) for key, value in ACCESS_LEVEL_CHOICES_DICT.items()
]

# Convert dictionary to list of tuples for description choices
ACCESS_LEVEL_DESCRIPTION_CHOICES = [
    (key, value[1]) for key, value in ACCESS_LEVEL_CHOICES_DICT.items()
]


# Define the AccessLevel model
class Permission(models.Model):
    name = models.CharField(
        max_length=100, unique=True, choices=ACCESS_LEVEL_NAME_CHOICES
    )
    description = models.TextField(
        blank=True, null=True, choices=ACCESS_LEVEL_DESCRIPTION_CHOICES
    )

    def __str__(self):
        return self.get_name_display()

# The reason I create another Member is because it is so unethical to change the base user model that django provides, so we clone it, sync it, and add more depth to it.
class Member(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    permissions = models.ManyToManyField(Permission, related_name="members", blank=True)
    # company_name = models.CharField(max_length=100)

    def __str__(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            return self.user.first_name
        elif self.user.last_name:
            return self.user.last_name
        else:
            return self.user.username


class WebClient(models.Model):
    """Web client users for the Demfirat Karven website"""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Will store hashed password
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    web_client_settings = models.JSONField(default=dict, blank=True)  # Store user preferences (notifications, theme, etc.)

    class Meta:
        db_table = 'web_client'
        verbose_name = 'Web Client'
        verbose_name_plural = 'Web Clients'

    def __str__(self):
        return self.username


class ExchangeRate(models.Model):
    currency_code = models.CharField(max_length=3, unique=True)  # USD, EUR, RUB, PLN
    rate = models.DecimalField(max_digits=10, decimal_places=4)  # Rate relative to TRY (e.g. 1 USD = 34.50 TRY)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exchange_rate'
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'

    def __str__(self):
        return f"{self.currency_code}: {self.rate}"


class ClientAddress(models.Model):
    """Multiple addresses for web clients"""
    client = models.ForeignKey(WebClient, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'client_address'
        verbose_name = 'Client Address'
        verbose_name_plural = 'Client Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.client.username} - {self.title}"

    def save(self, *args, **kwargs):
        if self.is_default:
            ClientAddress.objects.filter(client=self.client, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Favorite(models.Model):
    """Favorite products for web clients"""
    client = models.ForeignKey(WebClient, on_delete=models.CASCADE, related_name='favorites')
    product_sku = models.CharField(max_length=100)  # Store product SKU
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'client_favorite'
        verbose_name = 'Client Favorite'
        verbose_name_plural = 'Client Favorites'
        ordering = ['-created_at']
        unique_together = ['client', 'product_sku']  # Prevent duplicate favorites

    def __str__(self):
        return f"{self.client.username} - {self.product_sku}"


class CartItem(models.Model):
    """Shopping cart items for web clients"""
    client = models.ForeignKey(WebClient, on_delete=models.CASCADE, related_name='cart_items')
    product_sku = models.CharField(max_length=100)  # Main product SKU
    variant_sku = models.CharField(max_length=100, blank=True, null=True)  # Optional variant SKU
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)  # Support decimal quantities (e.g., 1.5m)
    
    # Custom Curtain Fields
    is_custom_curtain = models.BooleanField(default=False)
    custom_attributes = models.JSONField(blank=True, null=True)  # Store custom curtain specifications
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Calculated custom price
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'client_cart_item'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['-created_at']
        # Remove unique_together for custom curtains (each is unique)
        # unique_together = ['client', 'product_sku', 'variant_sku']

    def __str__(self):
        if self.is_custom_curtain:
            return f"{self.client.username} - Custom Curtain ({self.product_sku}) x {self.quantity}"
        variant_info = f" ({self.variant_sku})" if self.variant_sku else ""
        return f"{self.client.username} - {self.product_sku}{variant_info} x {self.quantity}"


class GoogleChatCredentials(models.Model):
    """Store Google OAuth credentials for Chat integration"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_chat_credentials')
    token = models.TextField()  # JSON stored token
    refresh_token = models.TextField(blank=True, null=True)
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Google Chat Credentials for {self.user.username}"
