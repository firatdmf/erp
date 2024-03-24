from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


# The reason I create another Member is because it is so unethical to change the base user model that django provides, so we clone it, sync it, and add more depth to it.
class Member(models.Model):
    user = models.OneToOneField(User, null=True, on_delete = models.CASCADE)
    company_name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.user)



