# myapp/forms.py
from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'due_date', 'contact','company','description']  # Specify the fields you want to include in the form
