from django import forms
from .models import EquityExpense, Income, Book, Asset, Stakeholder, EquityCapital, CashAccount
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
        # widgets = {
        #     "books" : forms.HiddenInput(),
        # }
    
    # def __init__(self,*args,**kwargs):
    #     book = kwargs.pop('book',None)
    #     super(StakeholderForm,self).__init__(*args,**kwargs)


        
# class EquityForm(forms.ModelForm):
#     class Meta:
#         model = Equity
#         fields = '__all__'
#         widgets = {
#             "book": forms.HiddenInput()
#         }


#     def __init__(self, *args, **kwargs):

#         book = kwargs.pop('book',None)
#         super(EquityForm, self).__init__(*args, **kwargs)
#         self.fields["stakeholder"].empty_label = "Select a stakeholder"


#         # # This ensures only the same book from the model can be selected with the cash categories (accounts)
#         # if book:
#         #     self.fields["CashCategory"].queryset = CashCategory.objects.filter(book=book)


#         # print(f'yooo the book pk is {book_pk}')
#         # self.fields['CashCategory'].queryset = 



class EquityCapitalForm(forms.ModelForm):
    class Meta:
        model = EquityCapital
        fields = "__all__"
        widgets = {
            "date_invested": forms.DateInput(attrs={"type": "date"}),
        }
        
    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book',None)
        super(EquityCapitalForm, self).__init__(*args, **kwargs)
        # self.fields["stakeholder"].empty_label = "Select a stakeholder"
        self.fields["date_invested"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(book=book)
        

        # print(f'yooo the book pk is {book_pk}')
        # self.fields['CashAccount'].queryset = 


class EquityExpenseForm(forms.ModelForm):
    class Meta:
        model = EquityExpense
        fields = "__all__"
        
