from django import template
from django.template.loader import render_to_string
from todo.models import Task
from .todo_filters import days_since,is_past_due

register = template.Library()

@register.simple_tag
def update_task(task_id):
    return render_to_string('todo/update_task.html',{'task_id':task_id})

@register.simple_tag
def task_component(sort_type,csrf_token,page_type):
    # print(sort_type)
    tasks = Task.objects.all()
    # if page_type=="report":
    #     print("report")
    # elif page_type=="dashboard":
    #     print("dashboard")
    return render_to_string('todo/components/tasks_display.html', {
        'tasks':tasks,
        'sort_type':sort_type,
        'page_type':page_type,
        'csrf_token':csrf_token,
        # 'company': company,
        # 'contact':contact,
        # 'note_form': note_form,
        # 'csrf_token': csrf_token,
        # 'history_entries': history_entries,
        # 'current_url':current_url,
    })
