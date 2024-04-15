from django import template
register = template.Library()
@register.filter
def task_dictsortreversed(sort_type):
    if(sort_type=="dictsortreversed"):
        return True
    else:
        return False
    


@register.filter
def task_sort(tasks, sort_type):
    if sort_type == 'dictsort':
        return tasks.order_by('due_date')
    elif sort_type == 'dictsortreversed':
        return tasks.order_by('-due_date')
    else:
        return tasks