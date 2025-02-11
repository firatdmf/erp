from django.db import models
from crm.models import Company, Contact
from authentication.models import Member
# from operating.models import Product
from django.utils import timezone
from operating.models import Product
# Create your models here.


# The books is to keep the separate entities apart for accounting, and operating purposes. Each business division can have its own book, and the accounting is done separately for each book.
class Book(models.Model):
    # Saving when the book was created
    created_at = models.DateTimeField(auto_now=True)
    # The name of the book, this is the name of the business division, or the project, or the company that the book is created for.
    name = models.CharField(max_length=50, unique=True)
    total_shares = models.PositiveIntegerField(default = 10000000)

    # This is how a data entry gets displayed in the admin panel and forms
    def __str__(self):
        return self.name


# We need the below model to link stakeholders to books. (A stakeholder is someone who has some ownership in one or more books)
class StakeholderBook(models.Model):
    # A stakeholder has to be a member (An employee or a partner that is registered in the system, and has a user account)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)
    # This is how you link the book to the stakeholder.
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    # This is the percentage of equity the stakeholder has in the book. (This is used to calculate the equity capital)
    equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    shares = models.PositiveIntegerField(default = 0)


    # This is to make sure that for each book, there is only one stakeholder with the same member (preventing redundancies and errors)
    class Meta:
        unique_together = ('member', 'book')

    def __str__(self):
        return f"{self.member} - {self.book.name} - {self.equity_percentage}%"

# We will use this to keep track of the currency of the cash accounts, and the transactions
class CurrencyCategory(models.Model):
    code = models.CharField(max_length=3, unique=True)  # e.g., USD, EUR, TRY
    name = models.CharField(max_length=50, unique=True) # e.g., US Dollar, Euro, Turkish Lira
    symbol = models.CharField(max_length=5, blank=True, null=True)  # e.g., $, €, ₺

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name_plural = "Currency Categories"


# Create cash model here, all cash transactions will be listed here.
class AssetCash(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name_plural = "Asset Cash"

    def __str__(self):
        return f"{self.currency.symbol} {self.balance} ({self.book})"


# List all your cash accounts: bank, and on hand. Each account has its own currency, and balance.
class CashAccount(models.Model):

    class Meta:
        verbose_name_plural = "Cash Accounts"

        # This makes sure for each book, there are unique named cash accounts
        constraints = [
            models.UniqueConstraint(fields=['book', 'name'], name='unique_book_cashaccount')
        ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)

    name = models.CharField(max_length=50, blank=False, null=False)

    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )

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
    
    # For each capital received, there is a stakeholder who deposited it.
    stakeholder = models.ForeignKey(
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

    note = models.TextField()

    def __str__(self):
        return (
            self.stakeholder.name
            + " "
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
        # return (self.cash_account.currency.symbol + str(self.amount))





class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"


class EquityRevenue(models.Model):
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
    invoice_number = models.CharField(max_length=20, unique=True, blank=True,null=True)


class EquityExpense(models.Model):
    class Meta:
        verbose_name_plural = "Equity Expenses"

    def __str__(self):
        try:
            # return f"{self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')} - {self.category.name}"
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
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    # account_balance = models.DecimalField(
    #     max_digits=10, decimal_places=2, unique=False, blank=True
    # )


        
class EquityDivident(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    stakeholder = models.ForeignKey(
        Member, on_delete=models.CASCADE, blank=True, null=True
    )
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


# delete below
class IncomeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Income Categories"


# delete this income model, create EquityRevenue instead. Also delete IncomeCategory and its fixture
class Income(models.Model):
    category = models.ForeignKey(
        IncomeCategory, on_delete=models.CASCADE, blank=True, null=True
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
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return f"{self.category.name} - {self.amount}"

        try:
            # return f"{self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')} - {self.category.name}"
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%d %B, %Y')} - {self.category.name}"
        except AttributeError:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')}"


class AssetCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name


# Equity: Capital + Rev - Exp - Dividends
# Cash, Land, Furniture, Accounts Receivable, Office Supplies
class Asset(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    created_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateField()
    depreciating = models.BooleanField(default=False)
    residual_value = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    useful_life_in_months = models.DecimalField(
        max_digits=10, decimal_places=0, blank=True, null=True
    )

    def __str__(self):
        return f"Book: {self.book.name}, Asset Category: {self.category}, Asset Name: {self.name}, Asset Value: {self.currency}{'{:20,.2f}'.format(self.value)}"


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
    

# If balance is positive, then it is accounts receivable, if negative, it is accounts payable
# set it up so you can add a contact or a company and possibly no more than one row for each contact or company, meaning each row unique contact + company
class AccountBalance(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=True, null=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, blank=True, null= True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, blank=True, null= True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE, blank=True, null=True)



class Liability(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    due_date = models.DateField()

    def __str__(self):
        return f"{self.name} - {self.value} {self.currency.code}"

class InTransfer(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    source = models.ForeignKey(CashAccount, on_delete=models.CASCADE, related_name="source")
    destination = models.ForeignKey(CashAccount, on_delete=models.CASCADE, related_name="destination")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.source.name} -> {self.destination.name} | {self.currency.symbol}{self.amount}"

class Transaction(models.Model):

    def __str__(self):
        return f"{self.type} | {self.currency.symbol}{self.value}"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, blank=True, null=True)
    type_pk = models.PositiveIntegerField(blank=True, null=True)
    account = models.ForeignKey(CashAccount, on_delete=models.CASCADE, blank=True, null=True)
    account_balance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

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


    # ----------------------------------------------------------------------

# def invoice_default():
#     return {"firat":"hello"}

# def invoice_due_date():
#     return timezone.now() + timezone.timedelta(days=30)

# class Invoice(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     # invoice_number = models.CharField(max_length=20, unique=True)
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     company = models.ForeignKey(Company, on_delete=models.RESTRICT, blank=False, null=False)
#     date = models.DateField(default = timezone.now)
#     due_date = models.DateField(default = invoice_due_date())
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
#     paid = models.BooleanField(default=False)

    # def save(self, *args, **kwargs):
    #     # Calculate the total amount by summing the prices of all related InvoiceItems
    #     self.total_amount = sum(item.quantity * item.price for item in self.invoiceitem_set.all())
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"Invoice {self.invoice_number}"

# class InvoiceItem(models.Model):
#     invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.DecimalField(max_digits=10, decimal_places=2)
#     price = models.DecimalField(max_digits=10, decimal_places=2)

#     def __str__(self):
#         # return f"{self.quantity} x {self.product.name} in {self.invoice.invoice_number}"

#     def get_total_price(self):
#         return self.quantity * self.price

    

# Not used for now
class Source(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    