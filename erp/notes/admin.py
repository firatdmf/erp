from django.contrib import admin
from .models import Note, NoteFile

class NoteFileInline(admin.TabularInline):
    model = NoteFile
    extra = 0
    readonly_fields = ('drive_link', 'drive_file_id')

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'priority', 'is_favorite', 'updated_at')
    list_filter = ('is_favorite', 'priority', 'is_deleted')
    search_fields = ('title', 'content', 'user__user__username')
    inlines = [NoteFileInline]

@admin.register(NoteFile)
class NoteFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'note', 'uploaded_by', 'created_at')
