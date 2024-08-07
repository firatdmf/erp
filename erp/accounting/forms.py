from django import forms
from .models import Expense, Income
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
        }

    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        # self.fields['date'].initial = date.today()
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This removed the empty label option and preselects the 1st option (USD)
        self.fields["currency"].empty_label = None
        self.fields["category"].empty_label = None


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["book","category", "amount", "currency", "description", "date" ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super(IncomeForm, self).__init__(*args, **kwargs)
        # self.fields['date'].initial = date.today()
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This removed the empty label option and preselects the 1st option (USD)
        self.fields["currency"].empty_label = None
        self.fields["category"].empty_label = None
