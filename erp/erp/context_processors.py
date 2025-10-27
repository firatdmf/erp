from crm.models import Contact, Company, ClientGroup, Supplier
from marketing.models import ProductCategory
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# This is for base view functions to work on everywhere

def last_ten_entities(request):
    # Only fetch last 10 of each type, then sort and limit again
    # This avoids loading ALL records into memory
    contacts = Contact.objects.order_by('-created_at')[:10].annotate(
        entry_type=Value("Contact", output_field=CharField())
    )
    companies = Company.objects.order_by('-created_at')[:10].annotate(
        entry_type=Value("Company", output_field=CharField())
    )
    combined_list = sorted(
        chain(contacts, companies), key=attrgetter("created_at"), reverse=True
    )[:10]
    return {'last_ten_entities':combined_list}

def client_groups(request):
    return {'client_groups': ClientGroup.objects.all()}

def product_categories(request):
    return {'product_categories': ProductCategory.objects.all()}

def suppliers(request):
    return {'suppliers': Supplier.objects.all()}
