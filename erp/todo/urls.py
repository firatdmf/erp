from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = 'todo'
urlpatterns = [
    # /todo/ used to render a dashboard whose template called a
    # {% task_component %} tag deleted back in 2024 and never replaced,
    # so the page had been a 500 ever since. The page and its view are
    # gone; the NAME stays, because four templates link to it, and it
    # now lands on the task list — which is what that page was for.
    path("", RedirectView.as_view(pattern_name="todo:tasks_list", permanent=False), name="index"),
    path('search/', views.search_contacts_and_companies, name='search_contacts_and_companies'),
    path('tasks/',views.TasksList.as_view(),name="tasks_list"),
    path('tasks/create/',views.CreateTask.as_view(),name="create_task"),
    path("tasks/<int:task_id>/complete_task",views.complete_task,name="complete_task"),
    # path('tasks/<int:pk>/edit', views.TaskUpdateView.as_view(), name='edit_task'),
    path('tasks/<int:pk>/update_task', views.EditTaskView.as_view(), name='update_task'),
    # path('tasks/<int:pk>/update_task', views.edit_task, name='update_task'),
    path("tasks/<int:task_id>/delete_task",views.delete_task,name="delete_task"),
    # AJAX endpoints for sidebar modal and inline editing
    path('tasks/<int:task_id>/edit_form', views.get_task_edit_form, name='get_task_edit_form'),
    path('tasks/<int:task_id>/update_ajax/', views.update_task_ajax, name='update_task_ajax'),
    path('tasks/<int:task_id>/detail/', views.task_detail_page, name='task_detail'),
    path('tasks/<int:task_id>/detail_ajax/', views.task_detail_ajax, name='task_detail_ajax'),
    path('tasks/attachments/<int:att_id>/delete/', views.delete_task_attachment, name='delete_task_attachment'),
    path('tasks/<int:task_id>/add_comment/', views.add_task_comment, name='add_task_comment'),
]
