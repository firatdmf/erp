"""The deployment's own identity — see erp/branding.py for how it is read.

One row, edited on the Settings page. Every field is optional: blank
means "no answer here", and the code default in settings.BRAND_DEFAULTS
stands. That way a fresh install prints correctly before anyone has
opened the page, and a company that licenses Nejum fills in what it
wants to change.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from erp.branding import clear_cache


class BrandProfile(models.Model):
    class Meta:
        verbose_name = _("Brand profile")
        verbose_name_plural = _("Brand profile")

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
        """The row, created empty on first use. Empty is a valid state:
        every field then falls back to settings."""
        row = cls.objects.first()
        if row is None:
            from django.conf import settings
            row = cls.objects.create(
                nejum_credit=bool(getattr(settings, "NEJUM_CREDIT", True)))
        return row
