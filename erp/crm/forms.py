from .models import Contact, Note, Company
from todo.models import Task
from datetime import date

# So I can get the django's url name instead of manually typing
from django.urls import reverse

# below is for creating forms
from django.forms import ModelForm
from django import forms
from collections import OrderedDict

class ContactCreateForm(ModelForm):

    # This is to allow user the enter company name so we can display matching companies in the DB, if it does not exist, we create a new company in the Database
    company_name = forms.CharField(
        required=False,
        label="Company Name",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                # this will be defined in the init function of this ContactForm class.
                "hx-get": "placeholder",
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": "#company-suggestions",
                "hx-params": "*",
                "id": "company_name",
            }
        ),
    )

    # Hidden fields to store JSON arrays
    emails_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "contact_emails_data"})
    )
    
    phones_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "contact_phones_data"})
    )

    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )

    task_name = forms.CharField(max_length=200, label="Task Name", required=False)
    task_due_date = forms.DateField(
        label="Task Due Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        initial=date.today(),
    )
    task_description = forms.CharField(
        widget=forms.Textarea, label="Task Description", required=False
    )

    def clean_emails_data(self):
        import json
        emails_str = self.cleaned_data.get("emails_data", "")
        if not emails_str:
            return []
        try:
            emails = json.loads(emails_str)
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            for email in emails:
                try:
                    validate_email(email)
                except DjangoValidationError:
                    raise forms.ValidationError(f"Invalid email: {email}")
            return emails
        except json.JSONDecodeError:
            return []
    
    def clean_phones_data(self):
        import json
        phones_str = self.cleaned_data.get("phones_data", "")
        if not phones_str:
            return []
        try:
            return json.loads(phones_str)
        except json.JSONDecodeError:
            return []

    class Meta:
        model = Contact
        # Bring all fields to the form
        # fields = "__all__"  
        exclude = ("company", "email", "phone")
        widgets = {
            "birthday": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].widget.attrs["hx-get"] = reverse("crm:company_search")
        self.fields["company_name"].widget.attrs["onblur"] = "setTimeout(function(){document.getElementById('company-suggestions').innerHTML='';}, 200);"

        # Move company_name to right after job_title
        fields = list(self.fields.items())
        new_fields = []
        for name, field in fields:
            new_fields.append((name, field))
            if name == "job_title":
                new_fields.append(("company_name", self.fields["company_name"]))
                new_fields.append(("company_suggestions", forms.CharField(required=False)))  # placeholder
        self.fields = OrderedDict(new_fields)

    # when the form is submitted (Saved), do this.
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set email and phone arrays
        instance.email = self.cleaned_data.get("emails_data", [])
        instance.phone = self.cleaned_data.get("phones_data", [])
        if commit:
            instance.save()
            if self.cleaned_data["note_content"]:
                Note.objects.create(
                    contact=instance, content=self.cleaned_data["note_content"]
                )
            if self.cleaned_data["task_name"] and self.cleaned_data["task_due_date"]:
                Task.objects.create(
                    contact = instance,
                    name=self.cleaned_data["task_name"],
                    due_date=self.cleaned_data["task_due_date"],
                    description=self.cleaned_data["task_description"],
                    member = instance.member,
                )
        return instance
    
class ContactUpdateForm(ModelForm):
    # Hidden fields to store JSON arrays
    emails_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "contact_emails_data"})
    )
    
    phones_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "contact_phones_data"})
    )
    
    def clean_emails_data(self):
        import json
        emails_str = self.cleaned_data.get("emails_data", "")
        if not emails_str:
            return []
        try:
            emails = json.loads(emails_str)
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            for email in emails:
                try:
                    validate_email(email)
                except DjangoValidationError:
                    raise forms.ValidationError(f"Invalid email: {email}")
            return emails
        except json.JSONDecodeError:
            return []
    
    def clean_phones_data(self):
        import json
        phones_str = self.cleaned_data.get("phones_data", "")
        if not phones_str:
            return []
        try:
            return json.loads(phones_str)
        except json.JSONDecodeError:
            return []
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set email and phone arrays
        instance.email = self.cleaned_data.get("emails_data", [])
        instance.phone = self.cleaned_data.get("phones_data", [])
        if commit:
            instance.save()
        return instance
    
    class Meta:
        model = Contact
        exclude = ["email", "phone"]


class CompanyForm(ModelForm):
    # Contact selector field
    contact_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "selected_contact_id"})
    )
    
    # Hidden fields to store JSON arrays
    emails_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "emails_data"})
    )
    
    phones_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "phones_data"})
    )
    
    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )
    task_name = forms.CharField(max_length=200, label="Task Name", required=False)
    task_due_date = forms.DateField(
        label="Task Due Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )
    task_description = forms.CharField(
        widget=forms.Textarea, label="Task Description", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task_due_date"].initial = date.today()

    def clean_emails_data(self):
        import json
        emails_str = self.cleaned_data.get("emails_data", "")
        if not emails_str:
            return []
        try:
            emails = json.loads(emails_str)
            # Validate each email
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            for email in emails:
                try:
                    validate_email(email)
                except DjangoValidationError:
                    raise forms.ValidationError(f"Invalid email: {email}")
            return emails
        except json.JSONDecodeError:
            return []
    
    def clean_phones_data(self):
        import json
        phones_str = self.cleaned_data.get("phones_data", "")
        if not phones_str:
            return []
        try:
            return json.loads(phones_str)
        except json.JSONDecodeError:
            return []
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set email and phone arrays
        instance.email = self.cleaned_data.get("emails_data", [])
        instance.phone = self.cleaned_data.get("phones_data", [])
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Company
        exclude = ["email", "phone"]  # Exclude ArrayFields, we'll handle them manually


class NoteForm(ModelForm):
    class Meta:
        model = Note
        fields = ["content"]
        # Below is the give the form text area a class so I can adjust the css later manually.
        widgets = {"content": forms.Textarea(attrs={"class": "note_form_text_input"})}
