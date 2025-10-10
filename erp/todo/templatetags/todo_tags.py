from django import template
from django.template.loader import render_to_string
from todo.models import Task
from .todo_filters import days_since, is_past_due
from django.utils import timezone

register = template.Library()


@register.simple_tag
def update_task(task_id):
    return render_to_string("todo/update_task.html", {"task_id": task_id})


@register.simple_tag()
# below is to allow passing context (the user)
# @register.inclusion_tag("todo/components/tasks.html", takes_context=True)
def tasks_component(sort_type, csrf_token, page_type, contact, company, path, member):
    # member = user.member
    today = timezone.now().date()
    # user = context["user"]
    if page_type == "dashboard":
        if contact:
            tasks = Task.objects.filter(contact=contact, completed=False)
        elif company:
            tasks = Task.objects.filter(company=company, completed=False)
        else:
            tasks = Task.objects.filter(completed=False)
    else:
        if contact:
            tasks = Task.objects.filter(contact=contact)
        elif company:
            tasks = Task.objects.filter(company=company)
        else:
            tasks = Task.objects.all()

    # if page_type=="report":
    #     print("report")
    # elif page_type=="dashboard":
    #     print("dashboard")
    return render_to_string(
        "todo/components/tasks.html",
        {
            "tasks": tasks,
            "sort_type": sort_type,
            # page type can be 'dashboard', 'report', 'crm:detail', etc.
            "page_type": page_type,
            "csrf_token": csrf_token,
            "path": path,
            "member": member,
            # "user": user,
            # 'company': company,
            # 'contact':contact,
            # 'note_form': note_form,
            # 'csrf_token': csrf_token,
            # 'history_entries': history_entries,
            # 'current_url':current_url,
        },
    )
