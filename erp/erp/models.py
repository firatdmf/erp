"""The deployment's own identity — see erp/branding.py for how it is read.

One row, edited on the Settings page. Every field is optional, and a
blank one prints blank: there is no second source behind the row.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from erp.branding import clear_cache


class BrandProfile(models.Model):
    class Meta:
        verbose_name = _("Brand profile")
        verbose_name_plural = _("Brand profile")

    # Last resort for an auto-minted product SKU or roll barcode, used
    # when the supplier's name yields no consonants to abbreviate — see
    # operating.views_warehouse._consonant_prefix. It reads as the
    # house's own code because that is whose goods they became.
    code_prefix = models.CharField(max_length=6, blank=True)

    # What customer documents sign with. A ledger Book can still override
    # it for its own paperwork (Book.brand_name), which is how two books
    # of one deployment trade under different names.
    display_name = models.CharField(max_length=200, blank=True)

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


class Attachment(models.Model):
    """A file hung off a record: a payment's bank slip, an expense's
    receipt, an order's customer PO, a purchase's supplier invoice, a
    contact's contract. See erp/attachments.py for how they are stored,
    lightened and served.

    The record is any model, through `record`; the model carries a
    GenericRelation named `attachments`, so deleting the record takes its
    files (and, through the post_delete signal below, their bytes) with it.

    The bytes live in the Bunny storage zone and the row keeps only the
    storage `path`, never a CDN URL: a reader goes through the record's
    login-required file route, so a file has no public address to leak or
    guess. `file` is only for a dev box running without Bunny.
    """

    record_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
    record_id = models.PositiveBigIntegerField()
    record = GenericForeignKey("record_type", "record_id")

    name = models.CharField(max_length=255)
    path = models.CharField(max_length=700, blank=True, help_text="Path inside the Bunny storage zone")
    file = models.FileField(upload_to="attachments/%Y/%m/", blank=True, null=True)
    size = models.PositiveIntegerField(default=0, help_text="Bytes")
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["record_type", "record_id"])]
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return self.name

    @property
    def extension(self):
        return self.name.rsplit(".", 1)[-1].upper() if "." in self.name else ""

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    @property
    def is_pdf(self):
        return self.content_type == "application/pdf"

    def pretty_size(self):
        n = self.size or 0
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024.0


def attachments_relation():
    """The GenericRelation a record model declares as `attachments`."""
    from django.contrib.contenttypes.fields import GenericRelation
    return GenericRelation("erp.Attachment", content_type_field="record_type",
                           object_id_field="record_id")


@receiver(post_delete, sender=Attachment)
def remove_attachment_bytes(sender, instance, **kwargs):
    """Take the file with the row — on the signal, because most rows die by
    their record's cascade rather than the delete button. A storage error
    is logged, not raised: the row is already gone, and an orphaned file is
    a better state than a refused delete."""
    if instance.path:
        try:
            from marketing.utils.bunny_storage import delete_from_bunny
            delete_from_bunny(instance.path)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Could not delete attachment bytes at %s", instance.path)
    elif instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Could not remove the local copy of attachment %s", instance.pk)
