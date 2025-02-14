from django.db import models
from crm.models import Company, Contact
from authentication.models import Member

# from operating.models import Product
from django.utils import timezone
from datetime import timedelta
from crm.models import Supplier
# from operating.models import Product
from django.core.exceptions import ValidationError

# Create your functions here.


# Define a function to calculate the default due date for the invoices
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
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    # This is the percentage of equity the stakeholder has in the book. (This is used to calculate the equity capital)
    shares = models.PositiveIntegerField(default=0)

    # This is to make sure that for each book, there is only one stakeholder with the same member (preventing redundancies and errors)
    class Meta:
        unique_together = ("member", "book")

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


class Invoice(models.Model):
    INVOICE_TYPE_CHOICES = [("proforma", "Proforma"), ("commercial", "Commercial")]
    created_at = models.DateTimeField(auto_now_add=True)
    # Pass the function itself. Otherwise, If you put paranthesis after the function name, django would run it once, and set it as default for all the new objects you create in future.
    due_cate = models.DateTimeField(default=default_due_date)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    items = models.JSONField("ItemsInfo", default=invoice_items_default)
    # invoice_details = models.JSONField(_(""), encoder=, decoder=)
    invoice_type = models.CharField(default="proforma", choices=INVOICE_TYPE_CHOICES)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def balance(self):
        return self.total - self.paid

    def __str__(self):
        return f"Invoice {self.pk} - {self.invoice_type}"


# Create cash model here, all cash transactions will be listed here.
class AssetCash(models.Model):
    class Meta:
        verbose_name_plural = "Asset Cash"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction = models.ForeignKey(
        "Transaction", on_delete=models.CASCADE, blank=True, null=True
    )

    # Each currency will dictate it's own balance
    currency_balance = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    def __str__(self):
        return f"{self.currency.symbol} {self.amount} currency's balance: {self.currency_balance} | ({self.book})"


class AssetInventoryRawMaterial(models.Model):
    class Meta:
        verbose_name_plural = "Asset Inventory Raw Materials"
        constraints = [
            models.UniqueConstraint(fields=['name', 'supplier'], name='unique_name_supplier')
        ]

    RAW_TYPE_CHOICES = [("direct", "Direct"), ("indirect", "Indirect")]
    UNIT_TYPE_CHOICES = [("units", "Unit"),("mt","Meter"),("kg","Kilogram")]
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    # name and supplier combination should be unique, so we won't have multiple entries of the same product.

    name = models.CharField(null=False, blank=False)
    supplier = models.ForeignKey(Supplier,on_delete=models.RESTRICT, null=True, blank=True)
    # If the user does not enter a stockID, make the stockID equal to the id of the object created.
    # preopulate it with the next availabe stockid
    stock_id = models.CharField(null=True, blank=True)
    receipt_number = models.CharField(null=True, blank=True)
    unit_of_measurement = models.CharField(choices=UNIT_TYPE_CHOICES,null=True, blank=True, default=UNIT_TYPE_CHOICES[0])
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # This should be selectable field
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    warehouse = models.CharField(null=True, blank=True)
    location = models.CharField(null=True, blank=True)
    # Do not delete the raw material inventory if you delete the supplier model. Give a warning if there is at least one raw material from that company. Delete only if there are no raw mat. from that company
    raw_type = models.CharField(choices=RAW_TYPE_CHOICES, default=RAW_TYPE_CHOICES[0])


    def __str__(self):
        return f"{self.book} | {self.name} - {self.supplier} - {self.quantity} {self.unit_of_measurement}"


class AssetInventoryGood(models.Model):
    class Meta:
        verbose_name_plural = "Asset Inventory Goods"

    STATUS_CHOICES = [("wip", "Work in Progress"), ("finished", "Finished Good")]
    UNIT_TYPE_CHOICES = [("units", "Unit"),("mt","Meter"),("kg","Kilogram")]
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=300, unique=True)
    # This should be selectable field
    unit_of_measurement = models.CharField(choices=UNIT_TYPE_CHOICES,null=True, blank=True, default=UNIT_TYPE_CHOICES[0])
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(choices=STATUS_CHOICES)
    warehouse = models.CharField(null=True, blank=True)
    location = models.CharField(null=True, blank=True)

    @property
    def unit_price(self):
        return self.unit_cost * 2


class AssetAccountsReceivable(models.Model):
    class Meta:
        verbose_name_plural = "Asset Accounts Receivables"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )

    # Link the invoice that this was created for
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, blank=True, null=True
    )

    # Overriding the clean method that is called during the model's validation process.
    # So we can manually add additional measures.
    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        if self.contact and self.company:
            raise ValidationError(
                "Only one of 'contact' or 'company' can be assigned, not both."
            )

    def __str__(self):
        if self.company:
            return f"{self.book} | {self.company} now owes you {self.currency.symbol}{self.amount} "
        elif self.contact:
            return f"{self.book} | {self.contact} now owes you {self.currency.symbol}{self.amount} "
        else:
            return f"{self.book} |{self.currency.symbol}{self.amount} "


class AssetAccountsPayable(models.Model):
    class Meta:
        verbose_name_plural = "Asset Accounts Payables"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = supplier = models.ForeignKey(Supplier,on_delete=models.RESTRICT, null=True, blank=True)
    receipt = models.CharField(null=True, blank=True)

    def __str__(self):
        return f"{self.book} | you now owe {self.currency.symbol}{self.amount} to {self.supplier}"


# List all your cash accounts: bank, and on hand. Each account has its own currency, and balance.
class CashAccount(models.Model):
    class Meta:
        verbose_name_plural = "Cash Accounts"

        # This makes sure for each book, there are unique named cash accounts, so we won't have reduntant accounts
        constraints = [
            models.UniqueConstraint(
                fields=["book", "name"], name="unique_book_cashaccount"
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
        return (
            f"{self.name} | Balance: {self.currency.symbol}{self.balance} ({self.book})"
        )


# This is when a stakeholder makes a contribution to the business, and the cash account is credited with the amount.
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
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    new_shares_issued = models.PositiveIntegerField()

    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return (
            self.member.user.first_name
            + " "
            + self.member.user.last_name
            + "("
            + self.book.name
            + ")"
            + " "
            + self.cash_account.name
            + " "
            + self.cash_account.currency.symbol
            + str(self.amount)
            + " "
            + str(self.date_invested)
        )


# There are two types of revenues: Revenue generated from sales, and from others (refunds issued to you, and cash rewards you received etc)
class EquityRevenue(models.Model):
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
    invoice_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
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


# class AssetAccountsReceivable(models.Model):
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     name = models.CharField(max_length=100)
#     value = models.DecimalField(max_digits=10, decimal_places=2)
#     currency = models.ForeignKey(
#         CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     due_date = models.DateField()
#     contact = models.ForeignKey(Contact, on_delete=models.CASCADE, blank=True, null=True)

#     def __str__(self):
#         return f"Book: {self.book.name}, Name: {self.name}, Value: {self.currency}{'{:20,.2f}'.format(self.value)}"


# # probably delete and make a new one
# class Liability(models.Model):
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     name = models.CharField(max_length=100)
#     description = models.CharField(max_length=200, blank=True, null=True)
#     value = models.DecimalField(max_digits=12, decimal_places=2)
#     currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
#     due_date = models.DateField()

#     def __str__(self):
#         return f"{self.name} - {self.value} {self.currency.code}"


# Used in transfers between cash accounts within the same book.
class InTransfer(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    source = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="source"
    )
    destination = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, related_name="destination"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.source.name} -> {self.destination.name} | {self.currency.symbol}{self.amount}"


# Keeping logs of all transactions
class Transaction(models.Model):

    def __str__(self):
        return f"{self.type} | {self.currency.symbol}{self.value}"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, blank=True, null=True)
    type_pk = models.PositiveIntegerField(blank=True, null=True)
    account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=True, null=True
    )
    account_balance = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )


# This model will be used to track the KPIs in real-time
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
