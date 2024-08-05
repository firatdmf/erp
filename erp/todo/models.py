from django.db import models

# Create your models here.
from django.utils import timezone
from django.urls import reverse
from crm.models import Contact, Company
# from authentication.models import Member
from datetime import datetime, date


class Task(models.Model):
    # blank=True: This parameter specifies whether the field is allowed to be blank in forms
    # null=True: This parameter specifies whether the field is allowed to have a null value in the database. If null=True, the field will be nullable in the database, meaning it can have a value of NULL. It applies to the database schema. Setting null=True means that the field can be empty in the database, but it may still be required in forms unless blank=True is also set.
    # So, in summary:
    # blank=True affects form validation.
    # null=True affects the database schema.
    
    task_name = models.CharField(max_length=200)
    due_date = models.DateField()
    description = models.TextField(blank=True,null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now_add=True,editable=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE,blank=True,  null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,blank=True,  null=True)


    def __str__(self):
        if(self.company):
            # return(self.task_name + "|"+self.company+"|")
            return f"{self.task_name} for | {self.company}"
        elif (self.contact):
            return f"{self.task_name} for | {self.contact}"
        else:
            return self.task_name

    #  Add a delete_url field to your Todo model to store the URL that will be used to delete the todo item.
    #  You can use the reverse function to generate this URL.
    def get_delete_url(self):
        return reverse('complete_task',args=[str(self.id)])


