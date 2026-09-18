"""Who this deployment is, and what its documents say.

The brand profile started life in settings.py (BRAND_DEFAULTS), which is
fine for the house but not for a company that licenses Nejum: nobody
edits a Python file to correct their own phone number. The values now
live in a database row anyone with admin rights can edit on the Settings
page, and settings.py holds the defaults that row falls back to.

    brand("BRAND_ADDRESS")   → the edited address, else the code default
    brand_flag("NEJUM_CREDIT")

Read through these two, never straight off `settings`, so an edit on the
Settings page reaches every document at once. The row is cached, and
saving it clears the cache.
"""
from django.conf import settings
from django.core.cache import cache

CACHE_KEY = "brand_profile_values"

# field on BrandProfile → the settings name it falls back to. Text fields
# only: blank means "not answered here", so the code default stands.
TEXT_FIELDS = {
    "display_name": "BRAND_DISPLAY_NAME",
    "legal_suffix": "BRAND_LEGAL_SUFFIX",
    "address": "BRAND_ADDRESS",
    "phone": "BRAND_PHONE",
    "fax": "BRAND_FAX",
    "email": "BRAND_EMAIL",
    "tax_office": "BRAND_TAX_OFFICE",
    "tax_number": "BRAND_TAX_NUMBER",
    "logo_url": "BRAND_LOGO_URL",
}
SETTING_TO_FIELD = {v: k for k, v in TEXT_FIELDS.items()}


def _values():
    """{setting name: edited value} for whatever the row actually answers.

    Cached, because every printed document asks several times. A missing
    table (before the migration runs, or in a test database being built)
    answers "nothing edited" rather than raising — a document must still
    print.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    values = {}
    try:
        from erp.models import BrandProfile
        row = BrandProfile.objects.first()
        if row is not None:
            for field, name in TEXT_FIELDS.items():
                text = (getattr(row, field, "") or "").strip()
                if text:
                    values[name] = text
            values["NEJUM_CREDIT"] = row.nejum_credit
    except Exception:
        values = {}
    cache.set(CACHE_KEY, values, 300)
    return values


def clear_cache():
    cache.delete(CACHE_KEY)


def brand(name, default=""):
    """A brand text value: what was edited, else what settings.py says."""
    edited = _values().get(name)
    if edited:
        return edited
    return (getattr(settings, name, "") or default or "").strip()


def brand_flag(name, default=False):
    """A brand on/off value, same precedence."""
    value = _values().get(name)
    if value is None:
        value = getattr(settings, name, default)
    return bool(value)


def brand_values():
    """Every brand text value, resolved — for the context processor."""
    return {name: brand(name) for name in TEXT_FIELDS.values()}
