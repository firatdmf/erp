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
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(
        max_length=100, verbose_name="Company Name (required)", unique=True
    )
    email = models.EmailField(blank=True)
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = models.CharField(max_length=15, blank=True)
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
    email = models.EmailField(blank=True)
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = models.CharField(max_length=15, blank=True)
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

    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        if not self.company_name and not self.contact_name:
            raise ValidationError(
                "You have to enter either, company name or contact name."
            )

    def __str__(self):
        return f"{self.company_name}"


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
    content = models.TextField()

    # below is for admin view
    def __str__(self):
        if self.contact:
            return f"Note for {self.contact}"
        elif self.company:
            return f"Note for {self.company}"
        else:
            return "Unassociated Note"


class CompanyFollowUp(models.Model):
    """
    Tracks automated follow-up emails sent to prospect companies.
    Follow-up schedule:
    - Email 1: 3 days after company creation
    - Email 2: 7 days after email 1 (10 days total)
    - Email 3: 14 days after email 2 (24 days total)
    - Email 4: 30 days after email 3 (54 days total)
    - Email 5: 60 days after email 4 (114 days total)
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
        """
        if not self.is_active or self.emails_sent_count >= 5:
            return False, 0

        # Schedule in days: [3, 7, 14, 30, 60]
        schedule = [3, 7, 14, 30, 60]
        
        from django.utils import timezone
        now = timezone.now()
        
        if self.emails_sent_count == 0:
            # First email: 3 days after company creation
            reference_date = self.company.created_at
            days_to_wait = schedule[0]
        else:
            # Subsequent emails: use last email sent date
            reference_date = self.last_email_sent_at
            days_to_wait = schedule[self.emails_sent_count]
        
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
