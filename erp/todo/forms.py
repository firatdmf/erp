# myapp/forms.py
from django import forms
from .models import Task


class HiddenInputWithStyle(forms.HiddenInput):
    def __init__(self, attrs=None, **kwargs):
        if attrs is None:
            attrs = {}
        attrs.update({'style': 'display:none;'})
        super().__init__(attrs=attrs, **kwargs)

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'due_date', 'contact','company','description',]  # Specify the fields you want to include in the form
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            # 'contact': HiddenInputWithStyle(),
            # 'company': HiddenInputWithStyle(),
            # 'contact': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
            # 'company': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
        }
