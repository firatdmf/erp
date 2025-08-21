from django.db import models, transaction
from crm.models import Company, Contact
from authentication.models import Member

# from operating.models import Product
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from crm.models import Supplier

from django.conf import settings

# from marketing.models import Product
from django.core.exceptions import ValidationError

# below two are for to make one model to point to different types of models.
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


# Create your functions here.


def get_base_currency():
    BASE_CURRENCY_CODE = getattr(
        settings, "BASE_CURRENCY_CODE", "USD"
    )  # if default currency is not defined in settings.py then set it to USD
    currency_category, created = CurrencyCategory.objects.get_or_create(
        code=BASE_CURRENCY_CODE
    )
    return currency_category


# Define a function to calculate the default due date for the invoices


from django.db.models import Sum
from decimal import Decimal


# def get_total_base_currency_balance():
#     base_currency = get_base_currency()
#     total_in_base = Decimal("0.00")

#     # Sum all cash accounts already in the base currency
#     base_currency_accounts = CashAccount.objects.filter(currency=base_currency)
#     base_currency_total = base_currency_accounts.aggregate(Sum("balance"))[
#         "balance__sum"
#     ] or Decimal("0.00")
#     total_in_base += base_currency_total

#     # Get a list of all non-base currency accounts
#     other_currency_accounts = CashAccount.objects.exclude(currency=base_currency)
#     for account in other_currency_accounts:
#         rate = get_exchange_rate(account.currency.code, base_currency.code)
#         if rate:
#             converted_balance = (account.balance * rate).quantize(Decimal("0.01"))
#             total_in_base += converted_balance

#     return total_in_base


def allowed_equity_models():
    # When filtering ContentType, use the lowercase model_name
    allowed_models = [
        "equitycapital",
        "equityrevenue",
        "equityexpense",
        "equitydivident",
        # "intransfer",
        # "currencyexchange",
    ]
    # allowed_cts = ContentType.objects.filter(model__in=allowed_models)
    return {
        "pk__in": ContentType.objects.filter(model__in=allowed_models).values_list(
            "pk", flat=True
        )
    }


def default_due_date():
    return timezone.now() + timedelta(days=15)


def invoice_items_default():
    return {
        "products": [
            {
                "id": 123,
                "price": 2,
                "quantity": 20,
            },
            {
                "id": 456,
                "price": 5,
                "quantity": 10,
            },
        ]
    }


# Create your models here.


# Fetch currency rates daily via services.py (runs when we save a CashTransactionEntry)
class CurrencyExchangeRate(models.Model):
    from_currency = models.CharField(max_length=3)  # e.g. 'USD'
    to_currency = models.CharField(max_length=3)  # e.g. 'EUR'
    rate = models.DecimalField(max_digits=20, decimal_places=6)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("from_currency", "to_currency", "date")

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate} {self.to_currency} on {self.date}"


# The books is to keep the separate entities apart for accounting, and operating purposes. Each business division can have its own book, and the accounting is done separately for each book.
class Book(models.Model):
    # Saving when the book was created
    created_at = models.DateTimeField(auto_now=True)
    # The name of the book, this is the name of the business division, or the project, or the company that the book is created for.
    name = models.CharField(max_length=50, unique=True)
    # Number of shares available. Will be used to calculate stake of each owner based on their shares
    total_shares = models.PositiveIntegerField(default=10000000)

    # This is how a data entry gets displayed in the admin panel and forms
    def __str__(self):
        return self.name


# We need the below model to link stakeholders to books. (A stakeholder is someone who has some ownership in one or more books)
class StakeholderBook(models.Model):
    # A stakeholder has to be a member (An employee or a partner that is registered in the system, and has a user account)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)
    # This is how you link the book to the stakeholder.
    book = models.ForeignKey(
        "Book", on_delete=models.CASCADE, related_name="stakeholders"
    )
    # This is the percentage of equity the stakeholder has in the book. (This is used to calculate the equity capital)
    shares = models.PositiveIntegerField(default=0)

    # This is to make sure that for each book, there is only one stakeholder with the same member (preventing redundancies and errors)
    class Meta:
        unique_together = ("member", "book")
        verbose_name_plural = "Stakeholder Books"

    def __str__(self):
        return f"{self.member.user.first_name + self.member.user.last_name} - {self.book.name} {self.shares}%"


# We will use this to keep track of the currency of the cash accounts, and the transactions
class CurrencyCategory(models.Model):
    code = models.CharField(max_length=3, unique=True)  # e.g., USD, EUR, TRY
    name = models.CharField(
        max_length=50, unique=True
    )  # e.g., US Dollar, Euro, Turkish Lira
    symbol = models.CharField(max_length=5, blank=True, null=True)  # e.g., $, €, ₺

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name_plural = "Currency Categories"


# Create cash model here, all cash transactions will be listed here.
# I do not think I need this model anymore
class AssetCash(models.Model):
    class Meta:
        verbose_name_plural = "Asset Cash"
        # ensuring there are no duplicate book and currency entries
        unique_together = ("book", "currency")

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False
    )

    # Each currency will dictate it's own balance
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # total_base_currency_balance = models.DecimalField(
    #     max_digits=10, decimal_places=2, blank=True, null=True
    # )

    def __str__(self):
        return f"Balance: {self.currency.symbol}{self.balance} | ({self.book})"


# ------- Raw Material -------

from operating.models import RawMaterialGood


class AssetInventoryRawMaterial(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=True, null=True)
    # from operating module
    raw_material_good = models.ForeignKey(RawMaterialGood, on_delete=models.CASCADE)

    @property
    def total_value(self):
        # e.g. FIFO/average calculation using related items
        return sum(
            [
                item.unit_cost * item.quantity
                for item in self.raw_material_good.items.all()
            ]
        )

    # def __str__(self):
    #     return self.raw_material_good_item.raw_material_good.name

    def __str__(self):
        try:
            return self.raw_material_good.name
        except AttributeError:
            return f"Raw Material #{self.pk or 'unsaved'}"


# class RawMaterialGoodsReceipt(models.Model):
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["supplier", "receipt_number"],
#                 name="unique_supplier_receipt_number",
#             )
#         ]

#     created_at = models.DateTimeField(auto_now_add=True)
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     supplier = models.ForeignKey(
#         Supplier, on_delete=models.RESTRICT, null=False, blank=False
#     )
#     receipt_number = models.CharField(blank=False, null=False, max_length=50)
#     date = models.DateField(blank=True, null=True)
#     # True if paid
#     payment_status = models.BooleanField(default=False)
#     cash_account = models.ForeignKey(
#         "CashAccount", on_delete=models.CASCADE, blank=True, null=True
#     )

#     # make custom validation for payment type
#     def clean(self):
#         # Validation check
#         if self.payment_status and not self.cash_account:
#             raise ValidationError(
#                 {
#                     "cash_account": "You must select a cash account when payment status is marked as paid."
#                 }
#             )

#         # Call the parent's clean() method to run other validations
#         super().clean()

#     def save(self, *args, **kwargs):
#         # Ensure validations run
#         self.full_clean()

#         # Automatically set the date to today if not provided
#         if not self.date:
#             self.date = timezone.now().date()
#         if self.payment_status == False:
#             self.cash_account = None

#         super().save(*args, **kwargs)

#     def total_cost(self):
#         total = 0
#         for item in self.items.all():
#             total += item.cost()
#         return total

#     def __str__(self):
#         return f"{self.book} | {self.supplier} | {self.date.strftime('%d %B, %Y') if self.date else 'No Date'}"


# class RawMaterialGoodsReceiptItem(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     receipt = models.ForeignKey(RawMaterialGoodsReceipt, on_delete=models.CASCADE, related_name="items")
#     raw_material = models.ForeignKey(AssetInventoryRawMaterial,on_delete=models.CASCADE)
#     quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

#     def cost(self):
#         return self.quantity * self.unit_cost

#     def __str__(self):
#         return f"{self.raw_material.book} | {self.raw_material.name} - {self.quantity} units"


# ------- Finished Goods -------


class AssetInventoryFinishedGood(models.Model):
    class Meta:
        verbose_name_plural = "Asset Inventory Goods"

    # product = models.ForeignKey(Product,models.RESTRICT, blank=True, null=True)
    STATUS_CHOICES = [("wip", "Work in Progress"), ("finished", "Finished Good")]

    created_at = models.DateTimeField(auto_now_add=True)
    # Set this to when the inventory moved from work in progress to finished.
    # Later will be used to measure the speed and efficiency.
    modified_at = models.DateField(blank=True, null=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=300, unique=True)

    # Default is USD, maybe I will delete this later.
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Maybe you sell by the meter, or in kilograms instead of units, so this will not be an integer field.
    # quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Unavailable (used for another order), Comitted (on the way coming), Available (ready to ship)
    stock_type = models.CharField(null=True, blank=True)

    # Product status, could be in progress, or finished. I probably will need more status
    status = models.CharField(choices=STATUS_CHOICES)

    # You can have multiple inventory entries with the same product because they might be at different warehouses or locations
    warehouse = models.CharField(null=True, blank=True)
    location = models.CharField(null=True, blank=True)

    @property
    def unit_price(self):
        return self.unit_cost * 2


class FinishedGoodsReceipt(models.Model):
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=["supplier", "receipt_number"],
    #             name="unique_supplier_receipt_number",
    #         )
    #     ]

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.RESTRICT, null=False, blank=False
    )
    receipt_number = models.CharField(blank=False, null=False, max_length=50)
    date = models.DateField(blank=True, null=True)

    payment_status = models.BooleanField(default=False)
    cash_account = models.ForeignKey(
        "CashAccount", on_delete=models.CASCADE, blank=True, null=True
    )

    # make custom validation for payment type
    def clean(self):
        # Validation check
        if self.payment_status and not self.cash_account:
            raise ValidationError(
                {
                    "cash_account": "You must select a cash account when payment status is marked as paid."
                }
            )

    def save(self, *args, **kwargs):
        # Automatically set the date to today if not provided
        if not self.date:
            self.date = timezone.now().date()
        if self.payment_status == False:
            self.cash_account = None
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        total = 0
        for item in self.items.all():
            total += item.unit_cost * item.quantity
        return total

    def __str__(self):
        return f"{self.book} | {self.supplier} | {self.date.strftime('%d %B, %Y') if self.date else 'No Date'}"


class FinishedGoodsReceiptItem(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    goods_receipt = models.ForeignKey(
        FinishedGoodsReceipt, on_delete=models.CASCADE, related_name="items"
    )
    finished_good = models.ForeignKey(
        AssetInventoryFinishedGood, on_delete=models.RESTRICT, blank=True, null=True
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.goods_receipt.book} | {self.finished_good.name} - {self.quantity} units"


# ----------------------------------------------------------------------------------------------------------------


class AssetAccountsReceivable(models.Model):
    class Meta:
        verbose_name_plural = "Asset Accounts Receivables"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="accounts_receivable",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="accounts_receivable",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="accounts_receivable",
    )
    paid = models.BooleanField(default=False)
    paid_to_cash_account = models.ForeignKey("CashAccount",on_delete=models.CASCADE, blank=True, null=True)

    # Overriding the clean method that is called during the model's validation process.
    # So we can manually add additional measures.
    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        # Only one of contact, company, or supplier can be set
        fields = [self.contact, self.company, self.supplier]
        set_fields = [f for f in fields if f]
        if len(set_fields) > 1:
            raise ValidationError(
                "Only one of 'contact', 'company', or 'supplier' can be assigned."
            )

    def __str__(self):
        if self.company:
            return f"{self.book} | {self.company} now owes you {self.currency.symbol}{self.amount} "
        elif self.contact:
            return f"{self.book} | {self.contact} now owes you {self.currency.symbol}{self.amount} "
        else:
            return f"{self.book} |{self.currency.symbol}{self.amount} "


class LiabilityAccountsPayable(models.Model):
    from operating.models import RawMaterialGoodReceipt

    class Meta:
        verbose_name_plural = "Liability Accounts Payables"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid = models.BooleanField(default=False)
    paid_with_cash_account = models.ForeignKey(
        "CashAccount", on_delete=models.CASCADE, blank=True, null=True
    )
    supplier = supplier = models.ForeignKey(
        Supplier, on_delete=models.RESTRICT, null=False, blank=False
    )
    # receipt = models.CharField(null=True, blank=True)
    # raw_goods_receipt = models.ForeignKey(
    #     RawMaterialGoodsReceipt, on_delete=models.CASCADE, blank=True, null=True
    # )
    raw_material_good_receipt = models.ForeignKey(
        RawMaterialGoodReceipt, on_delete=models.CASCADE, blank=True, null=True
    )
    finished_goods_receipt = models.ForeignKey(
        FinishedGoodsReceipt, on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return f"{self.book} | you now owe {self.currency.symbol}{self.amount} to {self.supplier}"

    def clean(self):
        super().clean()  # run parent first
        if self.raw_material_good_receipt and self.finished_goods_receipt:
            raise ValidationError(
                {
                    "receipt": "You cannot submit two different types of receipts at once. Pick either raw goods, or finished goods."
                }
            )

        if self.paid:
            if not self.paid_with_cash_account:
                raise ValidationError(
                    {
                        "CashAccount": "You cannot alter balance without specifying a valid cash account that makes the payment."
                    }
                )
            elif self.paid_with_cash_account.currency != self.currency:
                raise ValidationError(
                    {
                        "CashAccount": "Paid with Cash Account does not match the receipts currency."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# List all your cash accounts: bank, and on hand. Each account has its own currency, and balance.
class CashAccount(models.Model):
    class Meta:
        verbose_name_plural = "Cash Accounts"

        # This makes sure for each book, there are unique named cash accounts, so we won't have reduntant accounts
        constraints = [
            models.UniqueConstraint(
                fields=["book", "name", "currency"],
                name="unique_book_cashaccount_currency",
            )
        ]

    # Each book will have its own set of cash accounts
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, blank=False, null=False, default=1
    )

    name = models.CharField(max_length=50, blank=False, null=False)  # Chase USD

    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )

    # We will keep updating it so that the most recent entries balance will be our current cash balance of that account.
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} | {self.currency.code} | Balance: {self.currency.symbol}{self.balance} ({self.book})"

    def clean(self):
        if self.balance < 0:
            raise ValidationError({"balance": "balance cannot be less than zero."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# This is when a stakeholder makes a contribution to the business, and the cash account is credited with the amount.
# test with negative numbers,
class EquityCapital(models.Model):
    class Meta:
        verbose_name_plural = "Equity Capitals"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)

    # For each capital received, there is a member (stakeholder) who deposited it.
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, blank=False, null=False
    )
    date_invested = models.DateField()

    # The cash account where the capital is deposited
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    new_shares_issued = models.PositiveIntegerField()

    note = models.TextField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than 0."})

    def __str__(self):
        return f"Capital | {self.currency}{self.amount} {self.member}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# There are two types of revenues: Revenue generated from sales, and from others (refunds issued to you, and cash rewards you received etc)
class EquityRevenue(models.Model):
    from operating.models import Order

    REVENUE_TYPES = [("sales", "Sales"), ("other", "Other")]

    class Meta:
        verbose_name_plural = "Equity Revenues"

    def __str__(self):
        return f"{self.currency.symbol}{self.amount} | {self.cash_account.name}"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    # you link the sales here, if it does not have invoice number, then it is other income, not sales income (could be refunds issued to you, or cash rewards you received from your bank)
    order = models.ForeignKey(Order, on_delete=models.RESTRICT, blank=True, null=True)
    revenue_type = models.CharField(choices=REVENUE_TYPES, default="sales")


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"


class EquityExpense(models.Model):
    class Meta:
        verbose_name_plural = "Equity Expenses"

    def __str__(self):
        try:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%d %B, %Y')} - {self.category.name}"
        except AttributeError:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')}"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, blank=True, null=True
    )
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        default=1,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    # account_balance = models.DecimalField(
    #     max_digits=10, decimal_places=2, unique=False, blank=True
    # )


class EquityDivident(models.Model):
    class Meta:
        verbose_name_plural = "Equity Dividents"

    def __str__(self):
        return f"{self.book} | {self.member} is paid {self.currency.symbol}{self.amount} Divident on {self.date} "

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)


# Used in transfers between cash accounts within the same book.
class InTransfer(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    from_cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="source"
    )
    to_cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="destination"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, default=get_base_currency
    )
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.from_cash_account.name} -> {self.to_cash_account.name} | {self.currency.symbol}{self.amount}"

    def clean(self):

        self.currency = self.from_cash_account.currency
        if self.from_cash_account and self.to_cash_account:
            currency = CurrencyCategory.objects.get(
                pk=self.from_cash_account.currency.pk
            )
            self.currency = currency
            if self.from_cash_account.currency != self.to_cash_account.currency:
                raise ValidationError(
                    "The currencies of the source and destination accounts must match."
                )

        # return cleaned_data
        # return super().clean()

        # # if isinstance(self.from_cash_account, int):
        # #     self.from_cash_account = CashAccount.objects.get(pk=self.from_cash_account)
        # if self.from_cash_account and not self.currency_id:
        #     self.currency = self.from_cash_account.currency
        # if self.from_cash_account.currency.code != self.to_cash_account.currency.code:
        #     raise ValidationError(
        #         {
        #             "currency": "The currencies of the accounts must be same to make in transfer"
        #         }
        #     )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CurrencyExchange(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    from_cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="currency_exchange_source"
    )
    to_cash_account = models.ForeignKey(
        CashAccount,
        on_delete=models.CASCADE,
        related_name="currency_exchange_destination",
    )
    # currency_rate = amount = models.DecimalField(max_digits=10, decimal_places=5)
    from_amount = models.DecimalField(max_digits=10, decimal_places=2)
    to_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Exchange {self.from_cash_account.currency.symbol}{self.from_amount} | {self.from_cash_account.name} -> {self.to_cash_account.currency.symbol}{self.to_amount} | {self.to_cash_account.name} "

    def clean(self):
        # Validation check
        if self.from_cash_account == self.to_cash_account:
            raise ValidationError(
                {
                    "cash_account": "You cannot pick the same cash account for both accounts"
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# Keeping logs of all transactions
class CashTransactionEntry(models.Model):

    class Meta:
        verbose_name_plural = "Cash Transaction Entries"

    # content_type stores which model it points to (EquityCapital, EquityRevenue, etc).
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=allowed_equity_models,
        null=False,
        blank=False,
    )
    # object_id stores the primary key of that model instance.
    content_pk = models.PositiveIntegerField(null=False, blank=False)
    # related_object lets you access the actual related instance.
    content = GenericForeignKey("content_type", "content_pk")

    # you assign like this:
    # entry.equity = some_equity_capital_instance
    # entry.save()

    # and you filter like this:
    # TransactionEntry.objects.filter(content_type=ContentType.objects.get_for_model(EquityCapital), equity_pk=some_id)

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_amount_positive = models.BooleanField()
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE, default=1)
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=True, null=True
    )

    # ------------------- below are calculated automatically. -------------------------
    cash_account_balance = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )

    # # getting it from the get_base_currency function
    BASE_CURRENCY = (
        get_base_currency()
    )  # if base currency code is not defined, then make it just usd

    # for amount normalized to base currency (e.g. USD)
    amount_in_base_currency = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    total_base_currency_balance = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )

    # --------------------------------------------

    def __str__(self):
        return (
            f"Books:{self.book}, {self.content} | {self.currency.symbol}{self.amount}"
        )

    def get_base_currency_symbol_for_template():
        # return str(get_base_currency().symbol)
        return "hello"

    def save(self, *args, **kwargs):

        # self.total_base_currency_balance = get_total_base_currency_balance()

        if self.currency.code != self.BASE_CURRENCY.code:
            from .services import get_exchange_rate

            rate = get_exchange_rate(self.currency.code, self.BASE_CURRENCY.code)
            if rate:
                # quantize() method is used to round or format a decimal number to a specific number of decimal places while following a chosen rounding rule.
                self.amount_in_base_currency = (self.amount * rate).quantize(
                    Decimal("0.01")
                )
                try:
                    latest_cash_transaction_entry = CashTransactionEntry.objects.latest(
                        "pk"
                    )
                    if latest_cash_transaction_entry.total_base_currency_balance:

                        if self.is_amount_positive:
                            self.total_base_currency_balance = (
                                latest_cash_transaction_entry.total_base_currency_balance
                                + self.amount_in_base_currency
                            )
                        else:
                            self.total_base_currency_balance = (
                                latest_cash_transaction_entry.total_base_currency_balance
                                - self.amount_in_base_currency
                            )
                        # round down to zero if it is a too small number
                        if self.total_base_currency_balance < 0.1:
                            self.total_base_currency_balance = 0
                    else:
                        self.total_base_currency_balance = self.amount_in_base_currency
                except Exception as e:
                    print({"Exception error:": e})
                    self.total_base_currency_balance = self.amount_in_base_currency
                    pass

            else:
                self.amount_in_base_currency = None
        else:
            self.amount_in_base_currency = self.amount
            from django.core.exceptions import ObjectDoesNotExist

            try:
                latest_cash_transaction_entry = CashTransactionEntry.objects.latest(
                    "pk"
                )
                latest_total_base_currency_balance = (
                    latest_cash_transaction_entry.total_base_currency_balance
                )
                if latest_total_base_currency_balance:
                    if self.is_amount_positive:
                        self.total_base_currency_balance = (
                            latest_cash_transaction_entry.total_base_currency_balance
                            + self.amount
                        )
                    else:
                        self.total_base_currency_balance = (
                            latest_cash_transaction_entry.total_base_currency_balance
                            - self.amount
                        )
            except ObjectDoesNotExist:
                self.total_base_currency_balance = self.amount
        if not self.cash_account_balance:
            self.cash_account_balance = self.cash_account.balance

        super().save(*args, **kwargs)


# This model will be used to track the KPIs daily
class Metric(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    money_in = models.DecimalField(max_digits=12, decimal_places=2)
    money_out = models.DecimalField(max_digits=12, decimal_places=2)
    burn = models.DecimalField(max_digits=12, decimal_places=2)
    inventory = models.DecimalField(max_digits=12, decimal_places=2)
    accounts_receivable = models.DecimalField(max_digits=12, decimal_places=2)
    accounts_payable = models.DecimalField(max_digits=12, decimal_places=2)
    runway = models.DecimalField(max_digits=12, decimal_places=1)
    growth_rate = models.DecimalField(max_digits=12, decimal_places=1)
    default_alive = models.BooleanField(default=True)
