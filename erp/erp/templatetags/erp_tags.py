from django import template
from django.template.loader import render_to_string
from crm.models import Contact, Company
from django.utils import timezone
import datetime
import calendar
from django.conf import settings
# from django.utils.timezone import make_aware
import pytz
register = template.Library()


@register.simple_tag
def dashboard_component(csrf_token,path,member):

    # Below two lines result in the same thing but they give naive time warning so we fix it by setting the timezone
    # today = timezone.localtime(timezone.now()).date()
    # today = datetime.datetime.today().strftime('%Y-%m-%d')

    from todo.models import Task
    import json
    from collections import defaultdict
    from django.utils import timezone as django_timezone
    from django.db.models import Q
    from django.db.models.functions import TruncDate
    
    # ⚡ ULTRA FAST: Single aggregate query for all counts
    from django.db.models import Count, Q, Case, When, IntegerField
    from django.db.models.functions import TruncDate
    
    today_date = django_timezone.now().date()
    
    # ⚡ Single query for today's leads (contacts + companies)
    from django.db.models import Sum
    number_of_leads_added = (
        Contact.objects.filter(created_at__date=today_date).count() +
        Company.objects.filter(created_at__date=today_date).count()
    )
    
    # ⚡ Single query for all task counts (using aggregate)
    if member:
        task_counts = Task.objects.filter(completed=False).aggregate(
            pending=Count('id'),
            my_tasks=Count('id', filter=Q(member=member)),
            assigned=Count('id', filter=Q(created_by=member) & ~Q(member=member))
        )
        pending_tasks_count = task_counts['my_tasks']
        my_tasks_count = task_counts['my_tasks']
        assigned_tasks_count = task_counts['assigned']
    else:
        pending_tasks_count = Task.objects.filter(completed=False).count()
        my_tasks_count = 0
        assigned_tasks_count = 0
    
    # ⚡ Calendar data: Efficient grouping by date
    base_calendar_query = Task.objects.filter(completed=False)
    if member:
        base_calendar_query = base_calendar_query.filter(member=member)

    tasks_by_date_query = base_calendar_query.annotate(
        date=TruncDate('due_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Convert to dict
    tasks_by_date = {
        item['date'].strftime('%Y-%m-%d'): item['count']
        for item in tasks_by_date_query if item['date']
    }
    
    tasks_calendar_data = json.dumps(dict(tasks_by_date))
    
    return render_to_string('components/dashboard_new.html',{
        'csrf_token':csrf_token,
        'number_of_leads_added':number_of_leads_added,
        'pending_tasks_count':pending_tasks_count,
        'my_tasks_count':my_tasks_count,
        'assigned_tasks_count':assigned_tasks_count,
        'tasks_calendar_data':tasks_calendar_data,
        # 'country_of_the_day':country_of_the_day,
        'path':path,
        'member':member,
    })

@register.simple_tag
def test_component(csrf_token):
    return render_to_string('components/test_component.html',{'context':"This is the test page context","csrf_token":csrf_token})

@register.simple_tag
def search_component(csrf_token):
    return render_to_string('components/search_component.html',{'context':"This is the test page context","csrf_token":csrf_token})