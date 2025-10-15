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

admin.site.register(ClientGroup)


@admin.register(CompanyFollowUp)
class CompanyFollowUpAdmin(admin.ModelAdmin):
    list_display = ('company', 'is_active', 'emails_sent_count', 'last_email_sent_at', 'stopped_reason', 'created_at')
    list_filter = ('is_active', 'stopped_reason', 'emails_sent_count')
    search_fields = ('company__name', 'company__email')
    readonly_fields = ('created_at', 'last_email_sent_at', 'stopped_at')
    
    def get_readonly_fields(self, request, obj=None):
        # Make all tracking fields readonly when editing
        if obj:
            return self.readonly_fields + ('company', 'emails_sent_count')
        return self.readonly_fields
