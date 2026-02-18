from django.db import models
from django.conf import settings
from authentication.models import Member
from django.contrib.postgres.fields import ArrayField

class Note(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
        ('important', 'Important'),
        ('ideas', 'Ideas'),
        ('meeting', 'Meeting'),
    ]

    # Owner of the note
    user = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='notes')
    
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    snippet = models.CharField(max_length=500, blank=True, null=True, help_text="Text-only preview of content")

    # Meta fields
    is_favorite = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True) # Soft delete / Recycle bin
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='work', db_index=True)
    
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        # Auto-generate snippet from content
        if self.content:
            from django.utils.html import strip_tags
            text = strip_tags(self.content)
            self.snippet = text[:490] + "..." if len(text) > 490 else text
        else:
            self.snippet = ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class NoteFile(models.Model):
    """Files attached to notes (stored in Google Drive)"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255)
    drive_file_id = models.CharField(max_length=255)
    drive_link = models.URLField(max_length=500)
    uploaded_by = models.ForeignKey(Member, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

    def get_download_url(self):
        """Returns direct download link"""
        return f"https://drive.google.com/uc?export=download&id={self.drive_file_id}"
