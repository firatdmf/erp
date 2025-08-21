from django import forms
from django.forms import formset_factory, inlineformset_factory
from .models import *

# from operating.models import Product
from datetime import date


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = "__all__"


class StakeholderBookForm(forms.ModelForm):
    class Meta:
        model = StakeholderBook
        fields = "__all__"

        # This ensures the book field is hidden, and the value is passed from the view (via pk in the url)
        # If I had put in the exlude array, it would have passed null which is not what we want
        widgets = {
            "book": forms.HiddenInput(),
        }

        # We don't want to manually enter this data.
        exclude = ["shares"]


class AssetAccountsReceivableForm(forms.ModelForm):
    class Meta:
        model = AssetAccountsReceivable
        fields = "__all__"

        widgets = {
            "book": forms.HiddenInput(),
        }


class LiabilityAccountsPayableForm(forms.ModelForm):
    class Meta:
        model = LiabilityAccountsPayable
        fields = "__all__"

        widgets = {
            "book": forms.HiddenInput(),
            "balance": forms.HiddenInput(),
        }


class EquityCapitalForm(forms.ModelForm):
    class Meta:
        model = EquityCapital
        fields = "__all__"
        widgets = {
            "date_invested": forms.DateInput(attrs={"type": "date"}),
            # Hide the book field, and pass the value from the view (url)
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityCapitalForm, self).__init__(*args, **kwargs)

        self.fields["date_invested"].widget.attrs["value"] = date.today().strftime(
            "%Y-%m-%d"
        )

        if book:
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list(
                "member", flat=True
            )
            self.fields["member"].queryset = Member.objects.filter(pk__in=members)

            # Get the cash accounts assigned to the book
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")


class EquityRevenueForm(forms.ModelForm):
    class Meta:
        model = EquityRevenue
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
            # "invoice_number": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityRevenueForm, self).__init__(*args, **kwargs)
        # pre-populate the datefield with today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)


class EquityExpenseForm(forms.ModelForm):
    class Meta:
        model = EquityExpense
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    # This pre-populates form fields with given variables
    def __init__(self, *args, **kwargs):
        # You get the book variable from kwargs that was sent through the views.py file
        book = kwargs.pop("book", None)
        super(EquityExpenseForm, self).__init__(*args, **kwargs)
        # Set to today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)


class EquityDividentForm(forms.ModelForm):
    class Meta:
        model = EquityDivident
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityDividentForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list(
                "member", flat=True
            )
            self.fields["member"].queryset = Member.objects.filter(id__in=members)


class InTransferForm(forms.ModelForm):
    class Meta:
        model = InTransfer
        fields = "__all__"
        # exclude = ["currency"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(InTransferForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # self.fields["currency"].value =
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")


class CurrencyExchangeForm(forms.ModelForm):
    class Meta:
        model = CurrencyExchange
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
        }

    # from_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.filter(), empty_label="Select a cash account")
    # to_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
    # currency_rate = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    # amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
    # date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=date.today())
    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(CurrencyExchangeForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)


# ----------------------------------------------------------------------------------------------------------------
# below are added after august 4, 2025 and for the new cogs system
class AssetInventoryRawMaterialGoodForm(forms.ModelForm):
    class Meta:
        model = AssetInventoryRawMaterial
        fields = "__all__"
        # widgets = {
        #     # "book": forms.Select(attrs={"disabled": "disabled"}),  # dropdown, but uneditable
        #     # "date": forms.DateInput(attrs={"type": "date"}),
        # }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(AssetInventoryRawMaterialGoodForm, self).__init__(*args, **kwargs)
        # self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["book"].queryset = Book.objects.filter(pk=book.pk)


# below is for finished goods receipt


# class RawMaterialGoodsReceiptForm(forms.ModelForm):
#     class Meta:
#         model = RawMaterialGoodsReceipt
#         fields = "__all__"
#         exclude = ["book"]
#         labels = {"payment_status": "Paid"}
#         widgets = {
#             # "book": forms.Select(
#             #     attrs={"disabled": "disabled"}
#             # ),  # dropdown, but uneditable
#             "date": forms.DateInput(attrs={"type": "date"}),
#         }

#     def __init__(self, *args, **kwargs):
#         print("your book in the form is:", kwargs.get("book"))
#         book = kwargs.pop("book", None)
#         super(RawMaterialGoodsReceiptForm, self).__init__(*args, **kwargs)
#         self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

#         if book:
#             self.initial["book"] = book.pk
#             self.fields["cash_account"].queryset = CashAccount.objects.filter(
#                 book=book
#             ).order_by("name")


# class RawMaterialGoodsReceiptItemForm(forms.ModelForm):
#     # artificial field to replace the original raw_material field (to implement dynamic dropdown selection from database)
#     # raw_material_name = forms.CharField(label="Raw Material")

#     class Meta:
#         model = RawGoodsReceiptItem
#         fields = "__all__"

#         # exclude the original raw_material field
#         # exclude = ["raw_material"]

#     # def clean(self):
#     #     cleaned_data = super().clean()
#     #     name = cleaned_data.get("raw_material_name")
#     #     try:
#     #         material = AssetInventoryRawMaterial.objects.get(name__iexact=name)
#     #     except AssetInventoryRawMaterial.DoesNotExist:
#     #         material = AssetInventoryRawMaterial.objects.create(name=name)
#     #     cleaned_data["raw_material"] = material
#     #     return cleaned_data


# RawGoodsReceiptItemFormSet = inlineformset_factory(
#     parent_model=RawMaterialGoodsReceiptForm,
#     model=RawMaterialGoodsReceiptItem,
#     form=RawMaterialGoodsReceiptItemForm,
#     extra=1,
#     can_delete=True,
# )


# below is for finished goods receipt
class FinishedGoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = FinishedGoodsReceipt
        fields = "__all__"
        exclude = ["book"]
        labels = {"payment_status": "Paid"}
        widgets = {
            # "book": forms.Select(
            #     attrs={"disabled": "disabled"}
            # ),  # dropdown, but uneditable
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(FinishedGoodsReceiptForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        if book:
            print("your book pk is 2,", book.pk)
            self.initial["book"] = book.pk
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")


class FinishedGoodsReceiptItemForm(forms.ModelForm):

    class Meta:
        model = FinishedGoodsReceiptItem
        fields = "__all__"


FinishedGoodsReceiptItemFormSet = inlineformset_factory(
    parent_model=FinishedGoodsReceipt,
    model=FinishedGoodsReceiptItem,
    form=FinishedGoodsReceiptItemForm,
    extra=1,
    can_delete=True,
)


class PayLiabilityAccountsPayableForm(forms.Form):
    liability_accounts_payable = forms.ModelChoiceField(
        queryset=LiabilityAccountsPayable.objects.all(), label="Liability to Pay"
    )
    cash_account = forms.ModelChoiceField(
        queryset=CashAccount.objects.all(), label="Cash Account Used"
    )

    # This pre-populates form fields with given variables
    def __init__(self, *args, **kwargs):
        # You get the book variable from kwargs that was sent through the views.py file
        book = kwargs.pop("book", None)
        super(PayLiabilityAccountsPayableForm, self).__init__(*args, **kwargs)

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["liability_accounts_payable"].queryset = LiabilityAccountsPayable.objects.filter(
                book=book, paid=False
            ).order_by(("-pk"))
            # self.fields["book"].queryset = Book.objects.filter(book=book)

class GetAssetAccountsReceivableForm(forms.Form):
    asset_accounts_receivable = forms.ModelChoiceField(
        queryset=AssetAccountsReceivable.objects.all(), label="Receivable to get"
    )
    cash_account = forms.ModelChoiceField(
        queryset=CashAccount.objects.all(), label="Cash Account to deposit"
    )

    # This pre-populates form fields with given variables
    def __init__(self, *args, **kwargs):
        # You get the book variable from kwargs that was sent through the views.py file
        book = kwargs.pop("book", None)
        super(GetAssetAccountsReceivableForm, self).__init__(*args, **kwargs)

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["asset_accounts_receivable"].queryset = AssetAccountsReceivable.objects.filter(
                book=book, paid=False
            ).order_by(("-pk"))
            # self.fields["book"].queryset = Book.objects.filter(book=book)
