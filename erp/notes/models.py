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
    
    # Meta fields
    is_favorite = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False) # Soft delete / Recycle bin
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='work')
    
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional: Tags (if we want to use ArrayField for simple tagging like the design suggests "Labels")
    # For SQLite compatibility during dev, we might want to use JSONField or just a ManyToMany. 
    # But project uses Postgres in prod. Let's use simple JSONField or M2M if ArrayField is risky for local SQLite.
    # The 'todo' app has M2M tags or just text? 
    # Let's check 'todo' models again... ah, user environment says 'postgres' in settings but 'sqlite' in local?
    # settings.py: DATABASES['default']['ENGINE'] = config("DB_ENGINE")
    # Let's simpler approach: Separate Tag model or just JSONField if Django > 3.0 (it is 4.2).
    # Going with a simple separate model for Tags is safest and most flexible.
    # But design just shows "Labels" like "High Priority", "Medium Priority". Wait, those are priorities.
    # The design also shows "Tags" like "#planning", "#Q3".
    
    # Let's use a simple JSONField for tags to avoid extra tables for now, 
    # or just a CharField for "comma separated" if we want to be super simple. 
    # JSONField is best for modern Django.
    # tags = models.JSONField(default=list, blank=True) 
    
    class Meta:
        ordering = ['-updated_at']

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
