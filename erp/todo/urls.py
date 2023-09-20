from django.urls import path
from . import views

app_name = 'todo'
urlpatterns = [
    path("", views.index,name="index"),
    path("tasks/",views.CreateTask.as_view(),name="task_list"),
    path("tasks/",views.task_list.as_view(),name="task_list"),
    path("tasks/create_task",views.create_task,name="create_task"),
    path("tasks/<int:task_id>/complete_task",views.complete_task,name="complete_task"),
    path("tasks/<int:task_id>/delete_task",views.delete_task,name="delete_task"),
]