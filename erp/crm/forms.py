from .models import Contact, Note, Company
from todo.models import Task
from datetime import date
# below is for creating forms
from django.forms import ModelForm
from django import forms


class ContactForm(ModelForm):
    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )

    class Meta:
        model = Contact
        # Bring all fields to the form
        fields = "__all__"  #
        # except the company model itself
        exclude = ("company",)
        widgets = {
            "birthday": forms.DateInput(attrs={"type": "date"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            if self.cleaned_data["note_content"]:
                Note.objects.create(
                    company=instance, content=self.cleaned_data["note_content"]
                )
        return instance


class CompanyForm(ModelForm):
    note_content = forms.CharField(
        label="Initial Note", widget=forms.Textarea, required=False
    )
    task_name = forms.CharField(max_length=200, label="Task Name", required=False)
    due_date = forms.DateField(label="Due Date", widget=forms.DateInput(attrs={'type': 'date'}), required=False,initial=date.today())
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
        widgets = {
            'content':forms.Textarea(attrs={'class':'note_form_text_input'})
        }
