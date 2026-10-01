from django import forms
from django.utils.translation import gettext_lazy as _lazy
from .models import Note

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content', 'priority', 'category', 'is_favorite']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'note-title-input', 'placeholder': _lazy('Enter a title...')}),
            'content': forms.Textarea(attrs={'class': 'note-content-input', 'placeholder': _lazy('Enter the content...'), 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'note-select'}),
            'category': forms.Select(attrs={'class': 'note-select'}),
        }
