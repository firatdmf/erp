from crm.models import Contact, Company
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# This is for base view functions to work on everywhere

def last_five_entities(request):
    context = {}
    contacts = Contact.objects.all().annotate(
        entry_type=Value("Contact", output_field=CharField())
    )
    companies = Company.objects.all().annotate(
        entry_type=Value("Company", output_field=CharField())
    )
    combined_list = sorted(
        chain(contacts, companies), key=attrgetter("created_at"), reverse=True
    )
    # context['last_five_companies'] = Company.objects.all().order_by('-created_at')[:5]
    # context["last_five_entries"] = combined_list[:5]
    return {'last_five_entities':combined_list[:5]}
    # return context
