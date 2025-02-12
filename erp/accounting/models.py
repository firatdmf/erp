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
        return f"{self.currency.symbol} {self.amount} balance: {self.currency_balance} | ({self.book})"


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
        return(f"{self.book} | {self.member} is paid {self.currency.symbol}{self.amount} Divident on {self.date} ")

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
