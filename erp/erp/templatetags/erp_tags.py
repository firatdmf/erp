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

    # bring the timezone information from the settings and set to time zone variable via pytz library 
    timezone = pytz.timezone(settings.TIME_ZONE)
    
    # Get the current date and localize it so you won't get the naive time warning
    today = timezone.localize(datetime.datetime.today())

    # # There are 52 weeks in a year, this tells you which week of the day you are in (25th or 50th week etc)
    # week_number = datetime.date.today().isocalendar()[1] 
    # country_of_the_day = '' #initializing the variable
    # crm_countries = ['Spain','Italy','Portugal','Poland','Germany','France','Japan','Romania','Hungary','USA','Canada','UK'] # Countries to sell
    # if (today.weekday()!=6): #6th day is sunday (iterating from 0 as monday). We do not work on Sunday, so eliminate it.
    #     # If the week number is not even (in other words, odd) then select the first 6 countries from the list and pick one according to the day of the week, where 0 is monday
    #     # This is helpful to make sure we cover all the countries in the list
    #     if week_number % 2 != 0:
    #         # Pick among the first 6 countries
    #         country_of_the_day = crm_countries[:6][today.weekday()]
    #     else:
    #         # Pick among the last 6 countries
    #         country_of_the_day = crm_countries[-6:][today.weekday()]



    from todo.models import Task
    import json
    from collections import defaultdict
    
    # contact = Contact.objects.filter(name__icontains="firat")[0]
    start_of_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    contacts = Contact.objects.filter(created_at__gte=start_of_today)
    companies = Company.objects.filter(created_at__gte=start_of_today)
    number_of_leads_added = len(contacts) + len(companies)
    
    # Get all pending tasks with optimized query
    pending_tasks = Task.objects.filter(completed=False).select_related(
        'member', 
        'member__user',
        'company',
        'contact'
    )
    if member:
        pending_tasks = pending_tasks.filter(member=member) | pending_tasks.filter(member__isnull=True)
    
    # Use values to group by date efficiently (without loading full objects)
    from django.db.models.functions import TruncDate
    from django.db.models import Count
    tasks_by_date_query = pending_tasks.annotate(
        date=TruncDate('due_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Convert to dict format for JSON
    tasks_by_date = {}
    for item in tasks_by_date_query:
        if item['date']:
            date_str = item['date'].strftime('%Y-%m-%d')
            tasks_by_date[date_str] = item['count']
    
    pending_tasks_count = pending_tasks.count()
    
    tasks_calendar_data = json.dumps(dict(tasks_by_date))
    
    return render_to_string('components/dashboard.html',{
        'csrf_token':csrf_token,
        'number_of_leads_added':number_of_leads_added,
        'pending_tasks_count':pending_tasks_count,
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