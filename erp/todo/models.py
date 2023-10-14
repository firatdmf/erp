from django.db import models

# Create your models here.
from django.utils import timezone
from django.urls import reverse
from crm.models import Contact, Company
from authentication.models import Member
from datetime import datetime, date


class Task(models.Model):
    task_name = models.CharField(max_length=200)
    due_date = models.DateField()
    description = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE,blank=True,  null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,blank=True,  null=True)
    days_since_due = models.IntegerField(default=0)
    # member = models.OneToOneField


    def __str__(self):
        return(self.task_name)
    
    # To be able to save the days_since_due, we need to override the save model.
    def save(self, *args, **kwargs):
        # Calculate the number of days since due and store it in days_since_due field
        self.days_since_due = (date.today() - self.due_date).days
        super(Task, self).save(*args, **kwargs)
    
    #  Add a delete_url field to your Todo model to store the URL that will be used to delete the todo item.
    #  You can use the reverse function to generate this URL.
    def get_delete_url(self):
        return reverse('complete_task',args=[str(self.id)])


