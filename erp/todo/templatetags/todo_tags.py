from django import template
from django.template.loader import render_to_string
from todo.models import Task
register = template.Library()

@register.simple_tag
def task_component(sort_type,csrf_token,page_type):
    print(sort_type)
    tasks = Task.objects.all()
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