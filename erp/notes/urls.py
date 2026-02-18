from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.NoteListView.as_view(), name='index'),
    path('create/', views.NoteCreateView.as_view(), name='create'),
    path('note/<int:pk>/', views.NoteDetailView.as_view(), name='note_detail'),
    path('note/<int:pk>/delete/', views.NoteDeleteView.as_view(), name='delete'),
    path('note/<int:pk>/restore/', views.NoteRestoreView.as_view(), name='restore'),
    path('note/<int:pk>/toggle-favorite/', views.NoteToggleFavoriteView.as_view(), name='toggle_favorite'),
    path('note/<int:pk>/upload-file/', views.NoteFileUploadView.as_view(), name='upload_file'),
    path('note/<int:pk>/inline-edit/', views.NoteInlineEditView.as_view(), name='inline_edit'),
    path('file/<int:pk>/delete/', views.NoteFileDeleteView.as_view(), name='delete_file'),
]
