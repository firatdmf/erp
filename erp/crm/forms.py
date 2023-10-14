from .models import Contact, Note, Company
# below is for creating forms
from django.forms import ModelForm
from django import forms


class ContactForm(ModelForm):
    class Meta:
        model = Contact
        # Bring all fields to the form
        fields = '__all__' #
        # except the company model itself
        exclude = ('company',)
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }
class CompanyForm(ModelForm):
    class Meta:
        model = Company
        # Bring all fields to the form
        fields = '__all__' #

class NoteForm(ModelForm):
    class Meta:
        model = Note
        fields = ['content']


