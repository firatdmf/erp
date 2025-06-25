from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Contact)
admin.site.register(Company)
admin.site.register(Supplier)
# admin.site.register(Note)
# I am doing it like this so I can see the created at and modified dates.
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    # list_display = ('__all__',)
    list_display = ('id', 'contact', 'company', 'content', 'created_at', 'modified_date')


class CompanyAdmin(admin.ModelAdmin):
    search_fields = ["name", "email", "phone"]