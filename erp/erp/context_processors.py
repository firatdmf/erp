from crm.models import Contact, Company, ClientGroup, Supplier
from marketing.models import ProductCategory
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField
from django.core.cache import cache

# This is for base view functions to work on everywhere
# Made lazy to avoid unnecessary database queries on every page load

class LazyList:
    """Lazy evaluation wrapper for context processors"""
    def __init__(self, func):
        self.func = func
        self._cached = None
    
    def __iter__(self):
        if self._cached is None:
            self._cached = list(self.func())
        return iter(self._cached)
    
    def __len__(self):
        if self._cached is None:
            self._cached = list(self.func())
        return len(self._cached)
    
    def __bool__(self):
        return True

def last_ten_entities(request):
    """Lazy loading of last 10 entities - only executes when accessed in template"""
    def _get_entities():
        contacts = Contact.objects.order_by('-created_at')[:10].annotate(
            entry_type=Value("Contact", output_field=CharField())
        )
        companies = Company.objects.order_by('-created_at')[:10].annotate(
            entry_type=Value("Company", output_field=CharField())
        )
        combined_list = sorted(
            chain(contacts, companies), key=attrgetter("created_at"), reverse=True
        )[:10]
        return combined_list
    
    return {'last_ten_entities': LazyList(_get_entities)}

def client_groups(request):
    """Lazy loading of client groups - only executes when accessed in template"""
    return {'client_groups': LazyList(lambda: ClientGroup.objects.all())}

def product_categories(request):
    """Cached product categories - 5 minute cache"""
    categories = cache.get('product_categories_list')
    if categories is None:
        categories = list(ProductCategory.objects.all())
        cache.set('product_categories_list', categories, 300)  # 5 minutes
    return {'product_categories': categories}

def suppliers(request):
    """Cached suppliers - 5 minute cache"""
    suppliers_list = cache.get('suppliers_list')
    if suppliers_list is None:
        suppliers_list = list(Supplier.objects.all())
        cache.set('suppliers_list', suppliers_list, 300)  # 5 minutes
    return {'suppliers': suppliers_list}
