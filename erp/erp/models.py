"""The deployment's own identity — see erp/branding.py for how it is read.

One row, edited on the Settings page. Every field is optional, and a
blank one prints blank: there is no second source behind the row.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from erp.branding import clear_cache


class BrandProfile(models.Model):
    class Meta:
        verbose_name = _("Brand profile")
        verbose_name_plural = _("Brand profile")

    # The short label the ERP's own chrome uses — the mobile title, a
    # warehouse label, a sheet's heading.
    short_name = models.CharField(max_length=60, blank=True)
    # Last resort for an auto-minted product SKU or roll barcode, used
    # when the supplier's name yields no consonants to abbreviate — see
    # operating.views_warehouse._consonant_prefix. It reads as the
    # house's own code because that is whose goods they became.
    code_prefix = models.CharField(max_length=6, blank=True)

    # What customer documents sign with. A ledger Book can still override
    # it for its own paperwork (Book.brand_name), which is how two books
    # of one deployment trade under different names.
    display_name = models.CharField(max_length=200, blank=True)
    # Appended to the display name only when the name itself is unset —
    # see Book.effective_brand_name.
    legal_suffix = models.CharField(max_length=100, blank=True)

    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    fax = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=120, blank=True)
    tax_office = models.CharField(max_length=120, blank=True)
    tax_number = models.CharField(max_length=60, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    # The colour the house's own name prints in — its half of the credit
    # line at the foot of every document (erp/nejum_credit.py).
    brand_color = models.CharField(max_length=9, blank=True)

    # The "Created with Nejum" credit on customer documents
    # (erp/nejum_credit.py). Not blank-able: it is a yes or a no.
    nejum_credit = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    def __str__(self):
        return self.display_name or "Brand profile"

    def save(self, *args, **kwargs):
        # One row, always. A second would be a silent second identity, and
        # whichever the readers happened to pick would be the company.
        # Saving a "new" one therefore overwrites the row that exists —
        # which is an UPDATE, so the caller's force_insert has to go.
        if not self.pk:
            existing = BrandProfile.objects.values_list("pk", flat=True).first()
            if existing:
                self.pk = existing
                kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)
        clear_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        clear_cache()

    @classmethod
    def get(cls):
        """The row, created empty on first use."""
        return cls.objects.first() or cls.objects.create()


class WhatsAppSettings(models.Model):
    """The WhatsApp Business connection the "order shipped" message goes
    out through — see operating/order_whatsapp.py for how it is read.

    One row, edited under Integrations on the Settings page. A blank
    language or country code means the default (order_whatsapp.CONFIG_FIELDS).
    """
    class Meta:
        verbose_name = _("WhatsApp settings")
        verbose_name_plural = _("WhatsApp settings")

    # The switch: off keeps what was typed but sends nothing.
    enabled = models.BooleanField(default=True)
    # Meta's permanent (system user) token. Never shown back on the page.
    access_token = models.TextField(blank=True)
    phone_number_id = models.CharField(max_length=40, blank=True)
    # The approved template's name; every language code it is approved
    # in, comma-separated ("tr, en, ru"), from which a customer gets the
    # one for their phone number's country; and the language for every
    # other country.
    shipped_template = models.CharField(max_length=120, blank=True)
    template_languages = models.CharField(max_length=200, blank=True)
    template_language = models.CharField(max_length=10, blank=True)
    # Put in front of a customer's number typed without one ("0532 …").
    default_country_code = models.CharField(max_length=4, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    def __str__(self):
        return "WhatsApp settings"

    def save(self, *args, **kwargs):
        # One row, always — same reasoning as BrandProfile.save.
        if not self.pk:
            existing = WhatsAppSettings.objects.values_list("pk", flat=True).first()
            if existing:
                self.pk = existing
                kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """The row, created empty on first use."""
        return cls.objects.first() or cls.objects.create()
