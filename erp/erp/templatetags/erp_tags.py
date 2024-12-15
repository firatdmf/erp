from django import template
from django.template.loader import render_to_string
from crm.models import Contact, Company
from django.utils import timezone
import datetime
import calendar
register = template.Library()


country_index = 0
@register.simple_tag
def dashboard_component(csrf_token):
    today = timezone.localtime(timezone.now()).date()
    # today_day = (str(today)).split('-')[2]
    # below is the current week number of the current year
    week_number = datetime.date.today().isocalendar()[1] 
    country_of_the_day = '' #initializing the variable
    crm_countries = ['Spain','Italy','Portugal','Poland','Germany','France','Japan','Romania','Hungary','USA','Canada','UK']
    # We need to make sure today is not Sunday, because we do not work on Sundays (sunday is the 6th day of the week iterating from zero)
    if (today.weekday()!=6):
        # If the week number is not even (is odd) then select the first 6 countries from the list and pick one according to the day of the week, where 0 is monday
        if week_number % 2 != 0:
            country_of_the_day = crm_countries[:6][today.weekday()]
        else:
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