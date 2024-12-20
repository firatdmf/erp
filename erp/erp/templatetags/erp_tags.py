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
def dashboard_component(csrf_token):


    # Below two lines result in the same thing but they give naive time warning so we fix it by setting the timezone
    # today = timezone.localtime(timezone.now()).date()
    # today = datetime.datetime.today().strftime('%Y-%m-%d')

    # bring the timezone information from the settings and set to time zone variable via pytz library 
    timezone = pytz.timezone(settings.TIME_ZONE)
    
    # Get the current date and localize it so you won't get the naive time warning
    today = timezone.localize(datetime.datetime.today())

    # There are 52 weeks in a year, this tells you which week of the day you are in (25th or 50th week etc)
    week_number = datetime.date.today().isocalendar()[1] 
    country_of_the_day = '' #initializing the variable
    crm_countries = ['Spain','Italy','Portugal','Poland','Germany','France','Japan','Romania','Hungary','USA','Canada','UK'] # Countries to sell
    if (today.weekday()!=6): #6th day is sunday (iterating from 0 as monday). We do not work on Sunday, so eliminate it.
        # If the week number is not even (in other words, odd) then select the first 6 countries from the list and pick one according to the day of the week, where 0 is monday
        # This is helpful to make sure we cover all the countries in the list
        if week_number % 2 != 0:
            # Pick among the first 6 countries
            country_of_the_day = crm_countries[:6][today.weekday()]
        else:
            # Pick among the last 6 countries
            country_of_the_day = crm_countries[-6:][today.weekday()]



    # contact = Contact.objects.filter(name__icontains="firat")[0]
    contacts = Contact.objects.filter(created_at__gte=today)
    companies = Company.objects.filter(created_at__gte=today)
    number_of_leads_added = len(contacts) + len(companies)
    return render_to_string('components/dashboard.html',{
        'csrf_token':csrf_token,
        'number_of_leads_added':number_of_leads_added,
        'country_of_the_day':country_of_the_day,
    })

@register.simple_tag
def test_component(csrf_token):
    return render_to_string('components/test_component.html',{'context':"This is the test page context","csrf_token":csrf_token})

@register.simple_tag
def search_component(csrf_token):
    return render_to_string('components/search_component.html',{'context':"This is the test page context","csrf_token":csrf_token})