from django import template
from django.template.loader import render_to_string


register = template.Library()
@register.simple_tag
def dashboard_component(csrf_token):
    return render_to_string('components/dashboard.html',{
        'csrf_token':csrf_token
    })

@register.simple_tag
def test_component(csrf_token):
    return render_to_string('components/test_component.html',{'context':"This is the test page context","csrf_token":csrf_token})

@register.simple_tag
def search_component(csrf_token):
    return render_to_string('components/search_component.html',{'context':"This is the test page context","csrf_token":csrf_token})