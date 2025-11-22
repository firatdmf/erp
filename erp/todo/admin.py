from django.contrib import admin
from .models import Task, TaskComment
# Register your models here.

# admin.site.register(Task)
# I am registering admin panel manually so I can see the created_at, completed_at dates in the admin panel

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('author', 'content', 'created_at', 'updated_at')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'priority', 'due_date', 'member', 'completed', 'created_at', 'contact', 'company')
    list_filter = ('priority', 'completed', 'created_at')
    search_fields = ('name', 'description')
    inlines = [TaskCommentInline]

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'author', 'content', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'task__name')
