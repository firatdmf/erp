from crm.models import Contact, Company
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# This is for base view functions to work on everywhere

def last_ten_entities(request):
    contacts = Contact.objects.all().annotate(
        entry_type=Value("Contact", output_field=CharField())
    )
    companies = Company.objects.all().annotate(
        entry_type=Value("Company", output_field=CharField())
    )
    combined_list = sorted(
        chain(contacts, companies), key=attrgetter("created_at"), reverse=True
    )
    return {'last_ten_entities':combined_list[:10]}
