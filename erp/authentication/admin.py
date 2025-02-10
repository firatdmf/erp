from django.contrib import admin

from accounting.admin import StakeholderBookInline
from .models import Member, Permission
# Register your models here.

# admin.site.register(Member)

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('permissions',)
    inlines = (StakeholderBookInline,)

