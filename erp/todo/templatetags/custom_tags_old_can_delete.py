# You can delete this tag
# below is for creating custom components
from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag
def update_task(task_id):
    return render_to_string('todo/update_task.html',{'task_id':task_id})