from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Member(models.Model):
    user = models.OneToOneField(User, null=True, on_delete = models.CASCADE)
    company_name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.user)
