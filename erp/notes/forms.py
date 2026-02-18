from django import forms
from .models import Note

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content', 'priority', 'category', 'is_favorite']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'note-title-input', 'placeholder': 'Başlık girin...'}),
            'content': forms.Textarea(attrs={'class': 'note-content-input', 'placeholder': 'İçerik girin...', 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'note-select'}),
            'category': forms.Select(attrs={'class': 'note-select'}),
        }
