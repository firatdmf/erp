from django import forms
from .models import Expense, Income, Book, Asset, Capital, CashCategory, Stakeholder
from datetime import date


class ExpenseForm(forms.ModelForm):
    # category_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'category-input'}))

    class Meta:
        model = Expense
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
        #     "book" : forms.HiddenInput(),
        # }
    
    # def __init__(self,*args,**kwargs):
    #     book = kwargs.pop('book',None)
    #     super(StakeholderForm,self).__init__(*args,**kwargs)


        
class CapitalForm(forms.ModelForm):
    class Meta:
        model = Capital
        fields = '__all__'
        widgets = {
            "book": forms.HiddenInput()
        }


    def __init__(self, *args, **kwargs):

        book = kwargs.pop('book',None)
        super(CapitalForm, self).__init__(*args, **kwargs)
        self.fields["provider"].empty_label = "Select a stakeholder"


        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["CashCategory"].queryset = CashCategory.objects.filter(book=book)


        # print(f'yooo the book pk is {book_pk}')
        # self.fields['CashCategory'].queryset = 
