from django.db import models

# Create your models here.
import datetime
from django.utils import timezone
from django.urls import reverse

class Task(models.Model):
    task_name = models.CharField(max_length=200)
    due_date = models.DateField("Due date")
    description = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField()

    def __str__(self):
        return(self.task_name)
    
    #  Add a delete_url field to your Todo model to store the URL that will be used to delete the todo item.
    #  You can use the reverse function to generate this URL.
    def get_delete_url(self):
        return reverse('complete_task',args=[str(self.id)])


