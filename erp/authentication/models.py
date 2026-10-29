from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
ACCESS_LEVEL_CHOICES_DICT = {
    # Stored as "admin". Manages the books the member is assigned — their
    # warehouses, orders and purchases (erp.ownership.is_admin) — and
    # nothing that belongs to the install as a whole, which is a
    # superuser's (erp.ownership.is_install_admin).
    "admin": (
        "Manage their books",
        "Manages the warehouses, orders and purchases of the books they are "
        "assigned, confirming purchases included. Nothing install-wide.",
    ),
    # Stored as "manager", which sat unused until it was given this
    # meaning. Runs the warehouse and its stock, and has no business with
    # orders: not seeing them, not raising them. Enforced by
    # erp.middleware.ReadOnlyRoleMiddleware; see erp.roles.ORDER_PREFIXES.
    "manager": (
        "Operations manager",
        "Works the warehouse and its stock. Cannot see or create orders.",
    ),
    "employee": ("Employee", "Can access and manage their own tasks and projects."),
    "guest": ("Guest", "Has limited access to view certain resources."),
    # Granted per person rather than implied by rank: confirming a purchase
    # order turns it into real warehouse stock AND posts the debt to the
    # supplier, so it is held separately from "manager".
    "purchase_confirm": (
        "Confirm purchases",
        "Can confirm a purchase order into warehouse stock (goods receipt).",
    ),
    # Read-only, and narrower than "guest": a sales rep sees the two
    # things she quotes from — stock (quantity and price) and sales —
    # and cannot write anything anywhere. Enforced in one place, by
    # erp.middleware.ReadOnlyRoleMiddleware; see erp/roles.py.
    "sales_rep": (
        "Sales rep (read-only)",
        "Can view stock quantities, prices and sales. Cannot change anything.",
    ),
    # What an order cost us and what we made on it is the margin. Held as
    # a grant of its own rather than implied by "not a sales rep", so a
    # role can be given or refused the numbers without touching what
    # else it may do. Seeded to every existing non-rep member in
    # migration 0021; a new member has to be granted it.
    "view_profit": (
        "See cost and profit",
        "Can see cost of goods, gross profit and margin on orders and analytics.",
    ),
    # Labels go on the goods — rolls, stock items, packed sacks — which is
    # operations work. A grant of its own, so who prints them is decided
    # per person (erp.roles.may_print_labels). Seeded in migration 0030 to
    # every member who is not a sales rep.
    "print_labels": (
        "Print labels",
        "Can print stock, roll and package labels.",
    ),
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

class Role(models.Model):
    """A set of permissions people are given together — "Operations",
    "Sales rep" — and the people who hold it.

    A member is in one role at most, and a member in a role has exactly
    the role's permissions: they are written onto Member.permissions
    (authentication.member_roles), which is what every check in the app
    reads. A member in no role keeps whatever permissions they were given
    directly. Roles are made, renamed and filled by a superuser in
    Settings → Members & permissions.
    """
    name = models.CharField(max_length=60, unique=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# The reason I create another Member is because it is so unethical to change the base user model that django provides, so we clone it, sync it, and add more depth to it.
class Member(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    permissions = models.ManyToManyField(Permission, related_name="members", blank=True)
    # The role whose permissions this member has; see Role.
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True,
                             related_name="members")
    # company_name = models.CharField(max_length=100)

    # Which business this member works for. Orders they create, and the
    # customer accounts and invoices those raise, land in this book.
    #
    # Per MEMBER rather than per deployment: one install runs several
    # businesses, and which one a record belongs to is a fact about who
    # entered it, not about the server. Staff at the Laleli branch enter
    # Laleli's orders whatever anybody else is doing at the same moment.
    #
    # Null → fall back to their first assigned book, so a member who has
    # never picked one still books somewhere sensible rather than being
    # blocked. See accounting.services_accounts.get_default_book.
    default_book = models.ForeignKey(
        "accounting.Book",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="members",
        verbose_name="Working book",
        help_text="Orders this member creates are booked here.",
    )

    # Which books this member may work in at all. `default_book` is the one
    # of them they are working in right now — most people have exactly one
    # and never think about it; an admin holds several and switches.
    #
    # This is a permission boundary, not a convenience: the ledger views
    # filter on it, so a book that is not assigned is not reachable by
    # typing its id into the URL. Superusers are assigned every book
    # implicitly — see accounting.services_accounts.member_books.
    books = models.ManyToManyField(
        "accounting.Book",
        related_name="assigned_members",
        blank=True,
        verbose_name="Assigned books",
        help_text="Books this member may work in.",
    )

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
    # The CRM contact this customer's orders are charged to, made from
    # their own details on their first order (operating.web_orders). Kept
    # so a later order finds the same contact even after staff edit its
    # email; SET_NULL so merging the contact away just makes a new link.
    contact = models.ForeignKey(
        "crm.Contact", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="web_clients",
    )

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

    # The rolls the customer picked off the storefront's stock list
    # (operating/storefront_stock.py), by stock item id. Empty = "this
    # many, you choose". A line with rolls is the rolls: its quantity is
    # what they hold, and ordering it holds those very rolls.
    stock_items = models.JSONField(default=list, blank=True)

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
    # No longer read or written: the client comes from settings (see
    # google_credentials). Emptied by 0027; the columns go next release.
    client_id = models.TextField(blank=True, default="")
    client_secret = models.TextField(blank=True, default="")
    scopes = models.TextField()
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Google Chat Credentials for {self.user.username}"

    def google_credentials(self):
        """The account's google-auth Credentials. The ERP's OAuth client ID
        and secret come from settings, never from the row, so rotating the
        secret is one variable change and the table holds no secret."""
        from django.conf import settings
        from google.oauth2.credentials import Credentials
        return Credentials(
            token=self.token or None,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri or "https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=(self.scopes or "").replace(",", " ").split(),
        )
