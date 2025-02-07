from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
ACCESS_LEVEL_CHOICES_DICT = {
    'admin': ('Admin', 'Has full access to all resources and settings.'),
    'manager': ('Manager', 'Can manage teams and projects, but has limited access to settings.'),
    'employee': ('Employee', 'Can access and manage their own tasks and projects.'),
    'guest': ('Guest', 'Has limited access to view certain resources.'),
}

# Convert dictionary to list of tuples for name choices
ACCESS_LEVEL_NAME_CHOICES = [(key, value[0]) for key, value in ACCESS_LEVEL_CHOICES_DICT.items()]

# Convert dictionary to list of tuples for description choices
ACCESS_LEVEL_DESCRIPTION_CHOICES = [(key, value[1]) for key, value in ACCESS_LEVEL_CHOICES_DICT.items()]

# Define the AccessLevel model
class AccessLevel(models.Model):
    name = models.CharField(max_length=100, unique=True, choices=ACCESS_LEVEL_NAME_CHOICES)
    description = models.TextField(blank=True, null=True, choices=ACCESS_LEVEL_DESCRIPTION_CHOICES)

    def __str__(self):
        return self.get_name_display()

# The reason I create another Member is because it is so unethical to change the base user model that django provides, so we clone it, sync it, and add more depth to it.
class Member(models.Model):
    user = models.OneToOneField(User, null=True, on_delete = models.CASCADE)
    access_levels = models.ManyToManyField(AccessLevel, related_name='members')
    # company_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"



