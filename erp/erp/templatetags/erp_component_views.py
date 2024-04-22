from django import template
from django.template.loader import render_to_string


register = template.Library()
@register.simple_tag
def dashboard_component(csrf_token):
    return render_to_string('components/dashboard.html',{
        'csrf_token':csrf_token
    })
