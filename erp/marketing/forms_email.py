from django import forms
from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    """Form for creating and editing email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = ['name', 'sequence_number', 'subject', 'body', 'delay_amount', 'delay_unit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Introduction Email',
            }),
            'sequence_number': forms.Select(attrs={
                'class': 'form-input',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Use {{company_name}} for personalization',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 12,
                'placeholder': 'Email body... Use {{company_name}}, {{contact_name}} for personalization',
            }),
            'delay_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 1,
                'placeholder': 'e.g., 3',
            }),
            'delay_unit': forms.Select(attrs={
                'class': 'form-input',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
        labels = {
            'name': 'Template Name',
            'sequence_number': 'Email Sequence',
            'subject': 'Email Subject',
            'body': 'Email Body',
            'delay_amount': 'Wait Time',
            'delay_unit': 'Time Unit',
            'is_active': 'Active',
        }
        help_texts = {
            'subject': 'Available variables: {{company_name}}, {{contact_name}}, {{user_name}}',
            'body': 'Available variables: {{company_name}}, {{contact_name}}, {{user_name}}, {{user_title}}, {{user_company}}',
            'delay_amount': 'Email 1 sends immediately. For Email 2-6, this is the wait time after previous email',
            'delay_unit': 'Choose minutes for testing, hours/days for production',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        sequence_number = cleaned_data.get('sequence_number')
        
        # Check if template with same sequence already exists for this user
        if self.user and sequence_number:
            existing = EmailTemplate.objects.filter(
                user=self.user,
                sequence_number=sequence_number
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise forms.ValidationError(
                    f'You already have a template for Email {sequence_number}. '
                    f'Please edit the existing template or choose a different sequence number.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        template = super().save(commit=False)
        if self.user:
            template.user = self.user
        if commit:
            template.save()
        return template
