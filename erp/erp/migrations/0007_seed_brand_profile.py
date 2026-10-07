from decouple import config
from django.db import migrations

# What the documents printed while these values still lived in
# settings.py. The brand profile row is now the only place they are read
# from, so the row is given them once here — wherever it has no answer
# of its own — and nothing a customer receives changes on the day the
# settings go. An environment variable that overrode a default is
# honoured the same way it was.
FORMER_DEFAULTS = {
    "short_name": ("BRAND_NAME", "Demfirat"),
    "code_prefix": ("BRAND_CODE_PREFIX", "DMF"),
    "display_name": ("BRAND_DISPLAY_NAME", "DEMFIRAT® | Karven Home Collection"),
    "legal_suffix": ("BRAND_LEGAL_SUFFIX", "SAN. TİC. LTD. ŞTİ."),
    "address": ("BRAND_ADDRESS", "Ergene 1. OSB Mahallesi, D100 Cad. no.38 Ergene / TEKİRDAĞ"),
    "phone": ("BRAND_PHONE", "+90 (501) 057-1884"),
    "fax": ("BRAND_FAX", "+90 (282) 675-1552"),
    "email": ("BRAND_EMAIL", "info@demfirat.com"),
    "tax_office": ("BRAND_TAX_OFFICE", ""),
    "tax_number": ("BRAND_TAX_NUMBER", ""),
    "logo_url": ("BRAND_LOGO_URL", ""),
    "brand_color": ("BRAND_COLOR", "#944F05"),
}


def seed(apps, schema_editor):
    BrandProfile = apps.get_model("erp", "BrandProfile")
    row = BrandProfile.objects.first()
    if row is None:
        row = BrandProfile(
            nejum_credit=config("NEJUM_CREDIT", default=True, cast=bool))
    for field, (name, default) in FORMER_DEFAULTS.items():
        if not (getattr(row, field) or "").strip():
            setattr(row, field, config(name, default=default).strip())
    row.save()

    from erp.branding import clear_cache
    clear_cache()


class Migration(migrations.Migration):

    dependencies = [
        ("erp", "0006_brandprofile_short_name_code_prefix"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
