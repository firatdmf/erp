from django.contrib import admin
from .models import Member, AccessLevel
# Register your models here.

# admin.site.register(Member)

@admin.register(AccessLevel)
class AccessLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('access_levels',)