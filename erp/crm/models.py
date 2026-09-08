from django.conf import settings
from django.db import models

# To store array field use this
from django.contrib.postgres.fields import ArrayField
from django.forms import ValidationError

# Create your models here.

# Type of client
# class ClientType(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     status = models.TextField( choices=[("prospect", "Prospect"), ("qualified", "Qualified")],max_length=200, blank=True, )

#     def __str__(self):
#         return self.name


# group: tech
class ClientGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    # Who raised this record. Stamped automatically on first save by
    # erp.ownership.stamp_creator, from the request-scoped user. NULL on
    # rows that predate this column (and on anything created outside a
    # request); erp.ownership.can_edit treats those as admin-only.
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)ss",
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(
        max_length=100, verbose_name="Company Name (required)", unique=True
    )
    email = ArrayField(
        models.EmailField(max_length=254),
        blank=True,
        default=list,
        verbose_name="Email addresses"
    )
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
        verbose_name="Phone numbers"
    )
    website = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=50, blank=True)
    group = models.ForeignKey(
        ClientGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
    )
    status = models.CharField(
        choices=[("prospect", "Prospect"), ("qualified", "Qualified")],
        default=("prospect"),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class Contact(models.Model):
    # Who raised this record. Stamped automatically on first save by
    # erp.ownership.stamp_creator, from the request-scoped user. NULL on
    # rows that predate this column (and on anything created outside a
    # request); erp.ownership.can_edit treats those as admin-only.
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)ss",
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50, verbose_name="Contact Name (required)")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="contacts",
    )
    job_title = models.CharField(max_length=25, blank=True, verbose_name="Job Title")
    email = ArrayField(
        models.EmailField(max_length=254),
        blank=True,
        default=list,
        verbose_name="Email addresses"
    )
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
        verbose_name="Phone numbers"
    )
    address = models.TextField(max_length=255, blank=True)
    country = models.CharField(max_length=50, blank=True)
    birthday = models.DateField(null=True, blank=True)
    group = models.ForeignKey(
        ClientGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )

    def __str__(self):
        if self.company:
            return f"{self.name} | {self.company.name}"
        else:
            return self.name

    class Meta:
        verbose_name_plural = "Contacts"


class Supplier(models.Model):
    # the company name or contact name should be unique, I'll set that up later.
    company_name = models.CharField(max_length=300, null=True, blank=True)
    contact_name = models.CharField(max_length=300, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    website = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional links to existing CRM contact / company records so a
    # supplier can be associated with the same person/org you already
    # track elsewhere. Both blank — supplier may stand alone.
    linked_contact = models.ForeignKey(
        "Contact",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_suppliers",
    )
    linked_company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_suppliers",
    )

    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        if not self.company_name and not self.contact_name:
            raise ValidationError(
                "You have to enter either, company name or contact name."
            )

    def __str__(self):
        if self.company_name:
            return self.company_name
        elif self.contact_name:
            return self.contact_name
        return "Unnamed Supplier"


class Note(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    # If I delete the contact, then delete the notes associated to it.
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    content = models.TextField()

    # below is for admin view
    def __str__(self):
        if self.contact:
            return f"Note for {self.contact}"
        elif self.company:
            return f"Note for {self.company}"
        elif self.supplier:
            return f"Note for {self.supplier}"
        else:
            return "Unassociated Note"


class CompanyFollowUp(models.Model):
    """
    Tracks automated follow-up emails sent to prospect companies.
    Follow-up schedule:
    - Email 1: Sent immediately when company is created
    - Email 2: 3 days after email 1
    - Email 3: 7 days after email 2 (10 days total)
    - Email 4: 14 days after email 3 (24 days total)
    - Email 5: 30 days after email 4 (54 days total)
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="followup",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    emails_sent_count = models.IntegerField(default=0)
    stopped_reason = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Reason why follow-ups were stopped (e.g., 'status_changed', 'max_emails_reached', 'reply_received')"
    )
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Company Follow Ups"

    def __str__(self):
        return f"Follow-up for {self.company.name} - {self.emails_sent_count}/5 emails sent"

    def should_send_email(self):
        """
        Determines if a follow-up email should be sent based on schedule.
        Returns: (should_send: bool, days_to_wait: int)
        
        Note: Email 1 is sent immediately via signal, so this handles emails 2-5.
        """
        if not self.is_active or self.emails_sent_count >= 5:
            return False, 0

        # Email 1 is already sent immediately via signal
        # This handles emails 2-5 with schedule: [3, 7, 14, 30] days after previous email
        schedule = [3, 7, 14, 30]  # Days to wait after each email
        
        from django.utils import timezone
        now = timezone.now()
        
        # Emails 2-5: wait specified days after last email
        if self.emails_sent_count == 0:
            # Edge case: Email 1 wasn't sent for some reason, shouldn't happen
            return False, 0
        
        # Calculate which email we're about to send (2-5)
        next_email_index = self.emails_sent_count  # Since email 1 is already sent
        
        if next_email_index > len(schedule):
            return False, 0
        
        reference_date = self.last_email_sent_at
        days_to_wait = schedule[next_email_index - 1]  # -1 because email 1 is index 0
        
        days_elapsed = (now - reference_date).days
        return days_elapsed >= days_to_wait, days_to_wait

    def mark_email_sent(self):
        """Mark that an email was sent and increment counter."""
        from django.utils import timezone
        self.emails_sent_count += 1
        self.last_email_sent_at = timezone.now()
        
        if self.emails_sent_count >= 5:
            self.is_active = False
            self.stopped_reason = "max_emails_reached"
            self.stopped_at = timezone.now()
        
        self.save()

    def stop_followups(self, reason):
        """Stop follow-up emails for this company."""
        from django.utils import timezone
        self.is_active = False
        self.stopped_reason = reason
        self.stopped_at = timezone.now()
        self.save()


# Extensions that execute rather than describe. A CRM should carry
# whatever paperwork a customer sends, so the rule is open-minus-the-
# dangerous-ones rather than a whitelist: these are the endings that turn
# the file list into a way to hand a colleague a program, and nothing a
# salesperson legitimately attaches ends in one. A zipped executable
# still gets through — that is the accepted cost of accepting archives.
BLOCKED_ATTACHMENT_EXTENSIONS = frozenset({
    # Windows executables and installers
    "exe", "msi", "com", "scr", "pif", "cpl", "msc", "lnk", "reg",
    # Shell and script interpreters
    "bat", "cmd", "sh", "bash", "ps1", "psm1", "vbs", "vbe",
    "js", "jse", "wsf", "wsh", "hta",
    # Packaged applications
    "jar", "apk", "app", "deb", "rpm",
    # Macro-enabled Office documents — the classic mail-borne payload
    "docm", "dotm", "xlsm", "xltm", "xlam", "pptm", "potm", "ppam",
})


def validate_attachment_type(file):
    """Refuse the file endings that run instead of open.

    Only the LAST extension is examined, which is the point:
    "invoice.pdf.exe" is an executable wearing a document's name, and
    that is exactly the shape this is here to stop.
    """
    name = getattr(file, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in BLOCKED_ATTACHMENT_EXTENSIONS:
        raise ValidationError(
            f".{ext} files cannot be attached — programs and scripts are "
            f"not accepted. Put it in a zip if it really has to travel.")
    return file


def content_type_for(filename, declared=""):
    """Work out a file's type from its name, not from what the client said.

    The browser supplies `content_type` on an upload and a crafted client
    can supply anything, so trusting it lets a caller choose how their
    file is later served — declare a payload "image/svg+xml" and it comes
    back inline, on our own origin. The extension is not proof of content
    either, but it is at least ours to reason about, and the download view
    only ever renders a short list of types inline.
    """
    import mimetypes

    guess, _ = mimetypes.guess_type(filename or "")
    return (guess or declared or "application/octet-stream")[:120]


def validate_attachment_size(file):
    """Cap an attachment at 25 MB.

    Larger than the 10 MB product-image limit because these are the
    documents a salesperson hangs off a client — a signed contract scan
    or a spec sheet routinely runs past ten.
    """
    size_threshold = 26214400  # 25 MB
    if file.size > size_threshold:
        raise ValidationError("The maximum file size that can be uploaded is 25MB")
    return file


class Attachment(models.Model):
    """A file hung off a CRM record — contact, company or supplier.

    The bytes live in the Bunny Storage Zone and the row keeps only the
    storage `path` — never a CDN URL. Readers go through the
    login-required download view, which fetches from the Storage API
    with the account key, so an attachment has no public address to
    leak or guess.

    There is no local fallback for a failed upload. MEDIA_ROOT is a
    container path with no volume mounted: a file written there looks
    saved and is gone on the next deploy, which is how 3,611 warehouse
    rolls ended up pointing at photos that no longer exist. A refused
    upload the user can retry beats a file that quietly disappears.
    `file` is only for a dev box running without Bunny configured, where
    the local disk is the intent rather than a consolation prize.
    """

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    name = models.CharField(max_length=255)
    path = models.CharField(
        max_length=700, blank=True,
        help_text="Path inside the Bunny Storage Zone",
    )
    file = models.FileField(
        upload_to="crm/attachments/%Y/%m/", blank=True, null=True,
        validators=[validate_attachment_size, validate_attachment_type],
    )
    size = models.PositiveIntegerField(default=0, help_text="Bytes")
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        blank=True, null=True, related_name="crm_attachments",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name

    @property
    def href(self):
        """Every reader goes through the login-required download view."""
        from django.urls import reverse
        return reverse("crm:download_attachment", args=[self.pk])

    @property
    def extension(self):
        return (self.name.rsplit(".", 1)[-1].upper() if "." in self.name else "")

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    def pretty_size(self):
        n = self.size or 0
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024.0
