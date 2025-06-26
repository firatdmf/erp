from django.contrib import admin
from .models import Task
# Register your models here.

# admin.site.register(Task)
# I am registering admin panel manually so I can see the created_at, completed_at dates in the admin panel
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'due_date', 'description', 'completed', 'created_at', 'completed_at', 'contact', 'company')