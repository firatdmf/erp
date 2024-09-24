from django import forms
from .models import Expense, Income, Book, Asset
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


# class BookSelectionForm(forms.Form):
#     Book = forms.ModelChoiceField(queryset=Book.objects.all(), empty_label="Select a book")