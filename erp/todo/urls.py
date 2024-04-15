from django.urls import path
from . import views


app_name = 'todo'
urlpatterns = [
    path("", views.index.as_view(),name="index"),
    path('search/', views.search_contacts_and_companies, name='search_contacts_and_companies'),
    path("tasks/<int:task_id>/complete_task",views.complete_task,name="complete_task"),
    # path('tasks/<int:pk>/edit', views.TaskUpdateView.as_view(), name='edit_task'),
    path('tasks/<int:pk>/update_task', views.EditTaskView.as_view(), name='update_task'),
    # path('tasks/<int:pk>/update_task', views.edit_task, name='update_task'),
    path("tasks/<int:task_id>/delete_task",views.delete_task,name="delete_task"),
    path('task_report/',views.TaskReport.as_view(),name="task_report")
]