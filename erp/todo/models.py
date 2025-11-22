from django.db import models

# Create your models here.
from django.utils import timezone
from django.urls import reverse
from crm.models import Contact, Company

# from authentication.models import Member
from datetime import datetime, date
from authentication.models import Member


class Task(models.Model):
    # blank=True: This parameter specifies whether the field is allowed to be blank in forms
    # null=True: This parameter specifies whether the field is allowed to have a null value in the database. If null=True, the field will be nullable in the database, meaning it can have a value of NULL. It applies to the database schema. Setting null=True means that the field can be empty in the database, but it may still be required in forms unless blank=True is also set.
    # So, in summary:
    # blank=True affects form validation.
    # null=True affects the database schema.
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    name = models.CharField(max_length=200)
    due_date = models.DateField(db_index=True)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    completed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # make it either a company or contact
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_tasks')

    def __str__(self):
        if self.company:
            return f"{self.name} for | {self.company}"
        elif self.contact:
            return f"{self.name} for | {self.contact}"
        else:
            return self.name

    #  Add a delete_url field to your Todo model to store the URL that will be used to delete the todo item.
    #  You can use the reverse function to generate this URL.
    def get_delete_url(self):
        return reverse("complete_task", args=[str(self.id)])

    class Meta:
        indexes = [
            models.Index(fields=['completed', 'due_date']),
            models.Index(fields=['due_date', 'completed']),
            models.Index(fields=['priority', 'completed']),
            # ⚡ SEARCH OPTIMIZATION INDEXES
            models.Index(fields=['member', 'completed', 'priority', 'due_date']),  # My Tasks query
            models.Index(fields=['created_by', 'completed', 'member']),  # Delegated tasks query
            models.Index(fields=['name']),  # Search by name
        ]
        ordering = ['-priority', 'due_date']
        
    def save(self, *args, **kwargs):
        if not self.member and hasattr(self, "_current_member"):
            self.member = self._current_member
        super().save(*args, **kwargs)
    
    def get_priority_color(self):
        """Return color for priority badge"""
        colors = {
            'low': '#10b981',      # green
            'medium': '#f59e0b',   # orange
            'high': '#ef4444',     # red
            'urgent': '#dc2626',   # dark red
        }
        return colors.get(self.priority, '#6b7280')
    
    def get_priority_icon(self):
        """Return icon for priority"""
        icons = {
            'low': 'fa-arrow-down',
            'medium': 'fa-minus',
            'high': 'fa-arrow-up',
            'urgent': 'fa-exclamation-triangle',
        }
        return icons.get(self.priority, 'fa-minus')


class TaskComment(models.Model):
    """Comments on tasks for collaboration"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.task.name}"
