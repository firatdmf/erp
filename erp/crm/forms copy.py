from .models import Contact, Note, Company
from todo.models import Task

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
    due_date = forms.DateField(label="Due Date", widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    task_description = forms.CharField(
        widget=forms.Textarea, label="Task Description", required=False
    )

    class Meta:
        model = Company
        # Bring all fields to the form
        fields = "__all__"  #

    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     if commit:
    #         instance.save()
    #         if self.cleaned_data["note_content"]:
    #             Note.objects.create(
    #                 company=instance, content=self.cleaned_data["note_content"]
    #             )
    #     return instance
        
    def save(self, commit=True):
        # print('hello firat')
        # print(self.cleaned_data["note_content"])
        instance = super().save(commit=False)
        if commit:
            instance.save()
            note_content = self.cleaned_data.get("note_content")
            # if self.cleaned_data["note_content"]:
            if note_content:
                Note.objects.create(
                    company=instance, content=note_content
                )
            task_name = self.cleaned_data.get("task_name")
            due_date = self.cleaned_data.get("due_date")
            
            # if task_name and due_date and task_description:
            if task_name and due_date:
                task_description = self.cleaned_data.get("task_description","")
                Task.objects.create(
                    task_name=task_name,
                    due_date=due_date,
                    description=task_description,
                    company=instance,
                )
        return instance


class NoteForm(ModelForm):
    class Meta:
        model = Note
        fields = ["content"]
        # Below is the give the form text area a class so I can adjust the css later manually.
        widgets = {
            'content':forms.Textarea(attrs={'class':'note_form_text_input'})
        }
