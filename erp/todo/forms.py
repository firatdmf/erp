# myapp/forms.py
from django import forms
from .models import Task

from datetime import date
from django.utils import timezone

class HiddenInputWithStyle(forms.HiddenInput):
    def __init__(self, attrs=None, **kwargs):
        if attrs is None:
            attrs = {}
        attrs.update({'style': 'display:none;'})
        super().__init__(attrs=attrs, **kwargs)

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'due_date', 'priority', 'contact','company','description', 'member']  # Specify the fields you want to include in the form
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter task name'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'priority': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Enter task description'}),
            # 'due_date': forms.DateField(label="Due Date", widget=forms.DateInput(attrs={'type': 'date'}), required=False,initial=date.today()),
            # 'contact': HiddenInputWithStyle(),
            # 'company': HiddenInputWithStyle(),
            'contact': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
            'company': forms.HiddenInput(),  # Specify 'contact_company_id' as a hidden input here
            'member': forms.Select(attrs={'class': 'form-input'}),
        }

    # Below is to hide contact and company fields if the form has been used with parameter hide_fields=True
    def __init__(self, *args, **kwargs):
        hide_fields = kwargs.pop('hide_fields', False)  # Check if hide_fields parameter is passed
        current_member = kwargs.pop('current_member', None)  # Get current member if passed
        super(TaskForm, self).__init__(*args, **kwargs)
        
        # Optimize member queryset to avoid N+1 queries and potential cursor issues
        from authentication.models import Member
        self.fields['member'].queryset = Member.objects.select_related('user').all()
        
        # Initialize the due date as today's date
        if not self.instance.pk and 'due_date' in self.fields:
            self.fields['due_date'].widget.attrs['value'] = timezone.localdate().strftime('%Y-%m-%d')
            
        self.fields['name'].label = "Task name"
        self.fields['priority'].label = "Priority"
        self.fields['member'].label = "Assign to"
        
        # Set initial value for member field
        if current_member and not self.instance.pk:
            self.initial['member'] = current_member


        if hide_fields:
            # Remove Contact and Company fields from the form
            self.fields.pop('contact', None)
            self.fields.pop('company', None)
        else:
            # Optionally, you can set the fields as hidden fields
            self.fields['contact'].widget = forms.HiddenInput()
            self.fields['company'].widget = forms.HiddenInput()
    # -----------------------------------------------------------------------
