from django import forms

from .models import *
# from operating.models import Product
from datetime import date


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'



class StakeholderBookForm(forms.ModelForm):
    class Meta:
        model = StakeholderBook
        fields = '__all__'

        # This ensures the book field is hidden, and the value is passed from the view (via pk in the url)
        # If I had put in the exlude array, it would have passed null which is not what we want 
        widgets = {
            "book" : forms.HiddenInput(),
        }

        # We don't want to manually enter this data. 
        exclude = ['shares']

class AssetAccountsReceivableForm(forms.ModelForm):
    class Meta:
        model = AssetAccountsReceivable
        fields = "__all__"

        widgets = {
            "book" : forms.HiddenInput(),
        }

class LiabilityAccountsPayableForm(forms.ModelForm):
    class Meta:
        model = LiabilityAccountsPayable
        fields = "__all__"

        widgets = {
            "book" : forms.HiddenInput(),
        }

class EquityCapitalForm(forms.ModelForm):
    class Meta:
        model = EquityCapital
        fields = "__all__"
        widgets = {
            "date_invested": forms.DateInput(attrs={"type": "date"}),
            # Hide the book field, and pass the value from the view (url)
            "book": forms.HiddenInput(),
            "currency":forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityCapitalForm, self).__init__(*args, **kwargs)

        self.fields["date_invested"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        
        if book:
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list('member', flat=True)
            self.fields["member"].queryset = Member.objects.filter(id__in=members)

            # Get the cash accounts assigned to the book
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
        

class EquityRevenueForm(forms.ModelForm):
    class Meta:
        model = EquityRevenue
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
            "invoice_number": forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityRevenueForm, self).__init__(*args, **kwargs)
        # pre-populate the datefield with today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
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
        book = kwargs.pop('book',None)
        super(EquityExpenseForm, self).__init__(*args, **kwargs)
        # Set to today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
            # self.fields["book"].queryset = Book.objects.filter(book=book)
        

class EquityDividentForm(forms.ModelForm):
    class Meta:
        model = EquityDivident
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency":forms.HiddenInput(),
        }
    
    def __init__(self,*args,**kwargs):
        book = kwargs.pop('book',None)
        super(EquityDividentForm,self).__init__(*args,**kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list('member', flat=True)
            self.fields["member"].queryset = Member.objects.filter(id__in=members)





class InTransferForm(forms.Form):
    from_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.filter(), empty_label="Select a cash account")
    to_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=date.today())

    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(InTransferForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(book=book)
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(book=book)
            # self.fields["book"].queryset = Book.objects.filter(book=book)


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
        book = kwargs.pop('book',None)
        super(CurrencyExchangeForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(book=book)
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(book=book)
            # self.fields["book"].queryset = Book.objects.filter(book=book)
