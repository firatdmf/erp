from django.contrib import admin
from .models import Contact, Company, Note
# Register your models here.
admin.site.register(Contact)
admin.site.register(Company)
# admin.site.register(Note)
# I am doing it like this so I can see the created at and modified dates.
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    # list_display = ('__all__',)
    list_display = ('id', 'contact', 'company', 'content', 'created_at', 'modified_date')