from .models import Contact, Note, Company
from todo.models import Task
from datetime import date

# So I can get the django's url name instead of manually typing
from django.urls import reverse

# below is for creating forms
from django.forms import ModelForm
from django import forms
from collections import OrderedDict

class ContactForm(ModelForm):

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

    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )

    task_name = forms.CharField(max_length=200, label="Task Name", required=False)
    task_due_date = forms.DateField(
        label="Due Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        initial=date.today(),
    )
    task_description = forms.CharField(
        widget=forms.Textarea, label="Task Description", required=False
    )

    class Meta:
        model = Contact
        # Bring all fields to the form
        # fields = "__all__"  
        exclude = ("company",)
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
                )
        return instance


class CompanyForm(ModelForm):
    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )
    task_name = forms.CharField(max_length=200, label="Task Name", required=False)
    due_date = forms.DateField(
        label="Due Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
        initial=date.today(),
    )
    task_description = forms.CharField(
        widget=forms.Textarea, label="Task Description", required=False
    )

    class Meta:
        model = Company
        fields = "__all__"


class NoteForm(ModelForm):
    class Meta:
        model = Note
        fields = ["content"]
        # Below is the give the form text area a class so I can adjust the css later manually.
        widgets = {"content": forms.Textarea(attrs={"class": "note_form_text_input"})}
