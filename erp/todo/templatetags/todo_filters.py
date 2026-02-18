from django import template
from django.utils import timezone
from datetime import datetime, date
from django.utils.translation import gettext as _
register = template.Library()
@register.filter
def task_dictsortreversed(sort_type):
    if(sort_type=="dictsortreversed"):
        return True
    else:
        return False
    


@register.filter
def task_sort(tasks, sort_type):
    # Handle both QuerySet and list objects
    if hasattr(tasks, 'order_by'):
        # It's a QuerySet
        if sort_type == 'dictsort':
            return tasks.order_by('due_date')
        elif sort_type == 'dictsortreversed':
            return tasks.order_by('-due_date')
        else:
            return tasks
    else:
        # It's a list
        if sort_type == 'dictsort':
            return sorted(tasks, key=lambda x: x.due_date if x.due_date else date.max)
        elif sort_type == 'dictsortreversed':
            return sorted(tasks, key=lambda x: x.due_date if x.due_date else date.min, reverse=True)
        else:
            return tasks
    

    

@register.filter
def is_past_due(due_date):
    # return due_date <= timezone.now().date()
    if(days_since(due_date)==False):
        return False
    else:
        return True
    

# Below calculates the number of days passed between the date provided and now
# Below returns false if the due date is in the future
@register.filter(expects_localtime=True)
def days_since(value, arg=None):
    try:
        tzinfo = getattr(value, 'tzinfo', None)
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
        return value
    except ValueError:
        # Date arguments out of range
        return value
    today = datetime.now(tzinfo).date()
    delta = value - today
    
    # if abs(delta.days) == 1:
    #     day_str = _("day")
    # else:
    #     day_str = _("days")

    # if delta.days < 1:
    #     fa_str = _("ago")
    # else:
    #     fa_str = _("from now")

    # return "%s %s %s" % (abs(delta.days), day_str, fa_str)
    # if(delta.days < 0):
#         return (abs(delta.days))
#     # If the task is due today, then return False 
#     elif(delta.days == 0):
#         return False
#     else:
#         return

    # If the task is due display the number of days it was due
    if(delta.days < 0):
        return (str(abs(delta.days))+"d")
    # If the task is due today, then return False 
    elif(delta.days==0):
        return "today"
    else:
        return False

@register.filter
def can_edit(task, member):
    """
    Check if member can edit the task.
    Users can only edit tasks they created.
    If created_by is None (legacy tasks), assume editable.
    """
    if task.created_by:
        return task.created_by == member
    return True

@register.filter
def can_manage_team_task(task, user):
    """
    Check if user can manage (create/edit/delete) the team task.
    Allowed if user is admin or manager in the task's team.
    """
    if not user.is_authenticated:
        return False
        
    try:
        from team.models import TeamMember
        member = TeamMember.objects.filter(team=task.team, user=user).first()
        if member and member.role in ['admin', 'manager']:
            return True
    except Exception:
        pass
    return False