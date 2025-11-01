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

    name = models.CharField(max_length=200)
    due_date = models.DateField(db_index=True)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now_add=True, editable=True)
    # make it either a company or contact
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True)

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
        ]
        
    def save(self, *args, **kwargs):
        if not self.member and hasattr(self, "_current_member"):
            self.member = self._current_member
        super().save(*args, **kwargs)
