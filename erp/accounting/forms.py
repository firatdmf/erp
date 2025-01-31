from django import forms

from .models import EquityRevenue, EquityExpense, Income, Book, Asset, Stakeholder, EquityCapital, CashAccount, CurrencyCategory, EquityDivident, Invoice, InvoiceItem
from operating.models import Product
from datetime import date


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'

class ExpenseForm(forms.ModelForm):
    # category_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'category-input'}))

    class Meta:
        model = EquityExpense
        # fields = ['category','category_name', 'amount', 'currency','description','date']
        fields = ["book","category", "amount", "currency", "description", "date"]
        # fields = '__all__'
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        # self.fields['date'].initial = date.today()
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This removed the empty label option and preselects the 1st option (USD)
        self.fields["currency"].empty_label = None
        self.fields["category"].empty_label = None
        self.fields["book"].empty_label = None


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["book","contact","company","category", "amount", "currency", "description", "date" ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(IncomeForm, self).__init__(*args, **kwargs)
        # self.fields['date'].initial = date.today()
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This removed the empty label option and preselects the 1st option (USD)
        self.fields["currency"].empty_label = None
        self.fields["category"].empty_label = None
        self.fields["book"].empty_label = None






class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = '__all__'

class StakeholderForm(forms.ModelForm):
    class Meta:
        model = Stakeholder
        fields = '__all__'

        # Below creates problems for many to many fields, so we just do exclude instead
        # widgets = {
        #     "books" : forms.HiddenInput(),
        # }
        exclude = ['books', 'share']



    # def __init__(self, *args, **kwargs):
    #     super(StakeholderForm, self).__init__(*args, **kwargs)



class EquityCapitalForm(forms.ModelForm):
    class Meta:
        model = EquityCapital
        fields = "__all__"
        widgets = {
            "date_invested": forms.DateInput(attrs={"type": "date"}),
            # "book": forms.HiddenInput()
        }
        
    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityCapitalForm, self).__init__(*args, **kwargs)
        # self.fields["stakeholder"].empty_label = "Select a stakeholder"
        self.fields["date_invested"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # self.fields["book"].widget.attrs["value"] = book

        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
            # self.fields["book"].queryset = Book.objects.filter(book=book)
        

        # print(f'yooo the book pk is {book_pk}')
        # self.fields['CashAccount'].queryset = 


class EquityRevenueForm(forms.ModelForm):
    class Meta:
        model = EquityRevenue
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            # "book": forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityRevenueForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # self.fields["stakeholder"].empty_label = "Select a stakeholder"
        # self.fields["book"].widget.attrs["value"] = book

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
            "balance":forms.HiddenInput()
        }


    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityExpenseForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # self.fields["stakeholder"].empty_label = "Select a stakeholder"
        # self.fields["book"].widget.attrs["value"] = book

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
        }
    
    def __init__(self,*args,**kwargs):
        book = kwargs.pop('book',None)
        super(EquityDividentForm,self).__init__(*args,**kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)




class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields= ['invoice_number','company','due_date']
        widgets = {
            "due_date": forms.DateInput(attrs={"type":"date"}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'price']

        
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
    price = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Price can also be dynamic

class CreateInvoiceForm(forms.Form):
    invoice = InvoiceForm()
    items = forms.ModelMultipleChoiceField(queryset=Product.objects.all(), widget=forms.CheckboxSelectMultiple)


class InvoiceItemFormSet(forms.BaseFormSet):
    def clean(self):
        # Custom validation for the formset, e.g. if no items are selected
        if any(self.errors):
            return
        if not any(form.cleaned_data for form in self.forms):
            raise forms.ValidationError("At least one product must be added to the invoice.")
        
    

# class InTransferForm(forms.Form):
#     from_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
#     to_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
#     amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
#     date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=date.today())

#     def __init__(self, *args, **kwargs):
#         book = kwargs.pop('book',None)
#         super(InTransferForm, self).__init__(*args, **kwargs)
#         # This ensures only the same book from the model can be selected with the cash categories (accounts)
#         if book:
#             self.fields["from_cash_account"].queryset = CashAccount.objects.filter(book=book)
#             self.fields["to_cash_account"].queryset = CashAccount.objects.filter(book=book)
#             # self.fields["book"].queryset = Book.objects.filter(book=book)


class InTransferForm(forms.Form):
    from_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.filter(), empty_label="Select a cash account")
    to_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=date.today())

    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(InTransferForm, self).__init__(*args, **kwargs)
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(book=book)
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(book=book)
            # self.fields["book"].queryset = Book.objects.filter(book=book)