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
        fields = ['task_name', 'due_date', 'contact','company','description','contact']  # Specify the fields you want to include in the form
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            # 'contact': HiddenInputWithStyle(),
            # 'company': HiddenInputWithStyle(),
            # 'contact': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
            # 'company': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
        }

    # Below is to hide contact and company fields if the form has been used with parameter hide_fields=True
    def __init__(self, *args, **kwargs):
        hide_fields = kwargs.pop('hide_fields', False)  # Check if hide_fields parameter is passed
        super(TaskForm, self).__init__(*args, **kwargs)

        if hide_fields:
            # Remove Contact and Company fields from the form
            self.fields.pop('contact', None)
            self.fields.pop('company', None)
        else:
            # Optionally, you can set the fields as hidden fields
            self.fields['contact'].widget = forms.HiddenInput()
            self.fields['company'].widget = forms.HiddenInput()
    # -----------------------------------------------------------------------
