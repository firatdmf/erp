from django import forms
from .models import Expense, ExpenseCategory
from datetime import date

class ExpenseForm(forms.ModelForm):
    category_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'category-input'}))

    class Meta:
        model = Expense
        # fields = ['category_name', 'amount', 'date']
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        # self.fields['date'].initial = date.today()
        self.fields['date'].widget.attrs['value'] = date.today().strftime('%Y-%m-%d')