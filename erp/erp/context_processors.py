from crm.models import Contact, Company, ClientGroup, Supplier
from marketing.models import ProductCategory
from authentication.models import Member
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField
from django.core.cache import cache
from django.conf import settings as _settings


def ui_theme(request):
    """Expose the active UI theme name + brand identity to every template.

    Settings.py reads these from the active env profile (.env or
    .env.<ENV_PROFILE>) and stores them as Django constants. Templates
    use `{{ UI_THEME }}`, `{{ DB_SCHEMA }}`, `{{ BRAND_NAME }}`.
    """
    base = getattr(_settings, "STOREFRONT_PREVIEW_URL", "http://localhost:3010/")
    sep = "&" if "?" in base else "?"
    return {
        "UI_THEME": getattr(_settings, "UI_THEME", ""),
        "DB_SCHEMA": getattr(_settings, "DB_SCHEMA", "public"),
        "BRAND_NAME": getattr(_settings, "BRAND_NAME", "Nejum"),
        "STOREFRONT_PREVIEW_URL": base,
        "STOREFRONT_PREVIEW_URL_WITH_EDIT": f"{base}{sep}edit=1",
    }

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
    """Last 10 entities — evaluated eagerly inside the request so the
    queryset doesn't outlive the DB connection (lazy querysets were
    triggering 'connection already closed' on multi-tenant pages)."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'last_ten_entities': []}
    try:
        contacts = list(Contact.objects.order_by('-created_at')[:10].annotate(
            entry_type=Value("Contact", output_field=CharField())
        ))
        companies = list(Company.objects.order_by('-created_at')[:10].annotate(
            entry_type=Value("Company", output_field=CharField())
        ))
        combined_list = sorted(
            chain(contacts, companies), key=attrgetter("created_at"), reverse=True
        )[:10]
    except Exception:
        combined_list = []
    return {'last_ten_entities': combined_list}

def client_groups(request):
    """Cached client groups — 5 min TTL. Evaluated eagerly so template
    rendering can't outlive the DB connection."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'client_groups': []}
    cached = cache.get('client_groups_list')
    if cached is None:
        try:
            cached = list(ClientGroup.objects.all())
            cache.set('client_groups_list', cached, 300)
        except Exception:
            cached = []
    return {'client_groups': cached}

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

def all_members(request):
    """Cached members for task assignment — 5 min TTL. Evaluated eagerly
    to avoid lazy queryset surviving past the DB connection."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'all_members': []}
    members = cache.get('all_members_list')
    if members is None:
        try:
            members = list(Member.objects.select_related('user').all())
            cache.set('all_members_list', members, 300)
        except Exception:
            members = []
    return {'all_members': members}
