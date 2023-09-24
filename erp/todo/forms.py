# myapp/forms.py
from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'due_date', 'contact','company','description',]  # Specify the fields you want to include in the form
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            # 'contact': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
            # 'company': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
        }
