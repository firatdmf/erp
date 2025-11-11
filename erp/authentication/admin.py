from django.contrib import admin

from accounting.admin import StakeholderBookInline
from .models import Member, Permission, WebClient
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


@admin.register(WebClient)
class WebClientAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('username', 'email', 'name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'email', 'name', 'password')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
