"""Who this deployment is, and what its documents say.

The brand profile started life in settings.py, but nobody edits a Python
file to correct their own phone number. The values live in one database
row (erp.models.BrandProfile) that anyone with admin rights edits on the
Settings page, and that row is the only place a document reads them
from: a field left blank there prints blank.

    brand("BRAND_ADDRESS")   → the address on the row
    brand_flag("NEJUM_CREDIT")

Read through these two so an edit on the Settings page reaches every
document at once. The row is cached, and saving it clears the cache.
"""
from django.core.cache import cache

CACHE_KEY = "brand_profile_values"

# field on BrandProfile → the name its readers ask for it by. Text
# fields only.
TEXT_FIELDS = {
    "short_name": "BRAND_NAME",
    "display_name": "BRAND_DISPLAY_NAME",
    "legal_suffix": "BRAND_LEGAL_SUFFIX",
    "address": "BRAND_ADDRESS",
    "phone": "BRAND_PHONE",
    "fax": "BRAND_FAX",
    "email": "BRAND_EMAIL",
    "tax_office": "BRAND_TAX_OFFICE",
    "tax_number": "BRAND_TAX_NUMBER",
    "logo_url": "BRAND_LOGO_URL",
    "brand_color": "BRAND_COLOR",
    "code_prefix": "BRAND_CODE_PREFIX",
}
SETTING_TO_FIELD = {v: k for k, v in TEXT_FIELDS.items()}


def _values():
    """{name: value} for whatever the row actually answers.

    Cached, because every printed document asks several times. A missing
    table (before the migration runs, or in a test database being built)
    answers "nothing filled in" rather than raising — a document must
    still print.
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
    """A brand text value, off the profile row."""
    return _values().get(name) or default


def brand_flag(name, default=False):
    """A brand on/off value, off the profile row."""
    value = _values().get(name)
    return bool(default if value is None else value)


def brand_values():
    """Every brand text value, resolved — for the context processor."""
    return {name: brand(name) for name in TEXT_FIELDS.values()}
