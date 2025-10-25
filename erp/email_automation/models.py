from django.db import models
from django.contrib.auth.models import User
from crm.models import Company, Contact
from django.utils import timezone


class EmailAccount(models.Model):
    """Gmail account connected for sending/receiving emails"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_account')
    email_address = models.EmailField()
    
    # OAuth tokens
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.email_address} - {self.user.username}"
    
    class Meta:
        verbose_name = "Email Account"
        verbose_name_plural = "Email Accounts"


class EmailTemplate(models.Model):
    """Templates for the 6-email sequence"""
    SEQUENCE_CHOICES = [
        (1, 'Email 1 - Introduction'),
        (2, 'Email 2 - Follow-up'),
        (3, 'Email 3 - Value Proposition'),
        (4, 'Email 4 - Case Study'),
        (5, 'Email 5 - Last Chance'),
        (6, 'Email 6 - Final Follow-up'),
    ]
    
    TIME_UNIT_CHOICES = [
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=200)
    sequence_number = models.IntegerField(choices=SEQUENCE_CHOICES)
    subject = models.CharField(max_length=200)
    body = models.TextField(help_text="Use {{company_name}}, {{contact_name}} as placeholders")
    
    # Timing
    delay_amount = models.IntegerField(
        default=3,
        help_text="Time to wait after previous email (ignored for Email 1, which sends immediately)"
    )
    delay_unit = models.CharField(
        max_length=10,
        choices=TIME_UNIT_CHOICES,
        default='days',
        help_text="Unit for delay time"
    )
    
    # Legacy field for backwards compatibility
    days_after_previous = models.IntegerField(
        default=3,
        help_text="DEPRECATED: Use delay_amount and delay_unit instead"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence_number']
        unique_together = ['user', 'sequence_number']
    
    def __str__(self):
        return f"{self.get_sequence_number_display()} - {self.name}"


class EmailCampaign(models.Model):
    """Tracks email campaign for each company"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('stopped', 'Stopped - Reply Received'),
    ]
    
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='email_campaign')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_campaigns')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    emails_sent = models.IntegerField(default=0)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    next_email_scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    reply_received = models.BooleanField(default=False)
    reply_received_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Campaign for {self.company.name} - {self.emails_sent}/6 emails"
    
    class Meta:
        verbose_name = "Email Campaign"
        verbose_name_plural = "Email Campaigns"
    
    def should_send_next_email(self):
        """Check if next email should be sent"""
        if self.status != 'active':
            return False
        if self.emails_sent >= 6:
            return False
        if self.reply_received:
            return False
        if self.company.status != 'prospect':
            return False
        if self.next_email_scheduled_at and timezone.now() >= self.next_email_scheduled_at:
            return True
        return False
    
    def mark_reply_received(self):
        """Mark that a reply was received and update company status"""
        self.reply_received = True
        self.reply_received_at = timezone.now()
        self.status = 'stopped'
        self.save()
        
        # Update company status to qualified
        self.company.status = 'qualified'
        self.company.save()


class SentEmail(models.Model):
    """Record of each email sent"""
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='sent_emails')
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True)
    
    subject = models.CharField(max_length=200)
    body = models.TextField()
    
    # Gmail tracking
    gmail_message_id = models.CharField(max_length=200, blank=True)
    gmail_thread_id = models.CharField(max_length=200, blank=True)
    
    # Status
    sent_at = models.DateTimeField(auto_now_add=True)
    opened = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Sent Email"
        verbose_name_plural = "Sent Emails"


class ReceivedEmail(models.Model):
    """Record of emails received (replies)"""
    campaign = models.ForeignKey(
        EmailCampaign, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='received_emails'
    )
    
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=200, blank=True)
    
    subject = models.CharField(max_length=500)
    body = models.TextField()
    
    # Gmail tracking
    gmail_message_id = models.CharField(max_length=200, unique=True)
    gmail_thread_id = models.CharField(max_length=200, blank=True)
    
    # Metadata
    received_at = models.DateTimeField()
    processed = models.BooleanField(default=False)
    is_reply = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"From {self.sender_email} - {self.received_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-received_at']
        verbose_name = "Received Email"
        verbose_name_plural = "Received Emails"
