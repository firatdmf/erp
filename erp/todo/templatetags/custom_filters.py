from django import template
from django.utils import timezone
from datetime import datetime, date
from django.utils.translation import gettext as _
register = template.Library()

@register.filter
def is_past_due(due_date):
    # return due_date <= timezone.now().date()
    if(days_since(due_date)==False):
        return False
    else:
        return True
    

# Below calculates the number of days passed between the date provided and now
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