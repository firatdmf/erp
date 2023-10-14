from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def is_past_due(due_date):
    return due_date <= timezone.now().date()
