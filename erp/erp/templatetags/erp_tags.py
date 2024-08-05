from django import template
from django.template.loader import render_to_string
from crm.models import Contact, Company
from django.utils import timezone
import datetime
register = template.Library()
@register.simple_tag
def dashboard_component(csrf_token):
    today = timezone.localtime(timezone.now()).date()
    # print(today)
    # contact = Contact.objects.filter(name__icontains="firat")[0]
    contacts = Contact.objects.filter(created_at__gte=today)
    companies = Company.objects.filter(created_at__gte=today)
    number_of_leads_added = len(contacts) + len(companies)
    return render_to_string('components/dashboard.html',{
        'csrf_token':csrf_token,
        'number_of_leads_added':number_of_leads_added,
    })

@register.simple_tag
def test_component(csrf_token):
    return render_to_string('components/test_component.html',{'context':"This is the test page context","csrf_token":csrf_token})

@register.simple_tag
def search_component(csrf_token):
    return render_to_string('components/search_component.html',{'context':"This is the test page context","csrf_token":csrf_token})