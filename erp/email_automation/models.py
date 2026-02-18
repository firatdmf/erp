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


# ============================================================
# MY EMAILS - User's personal email management
# ============================================================
from django.contrib.postgres.fields import ArrayField


class Email(models.Model):
    """
    Kullanıcının gönderdiği/aldığı tüm e-postalar.
    Gmail ile senkronize edilir ve CRM entegrasyonu sağlar.
    """
    FOLDER_CHOICES = [
        ('inbox', 'Gelen Kutusu'),
        ('sent', 'Gönderilen'),
        ('archive', 'Arşiv'),
        ('trash', 'Silinenler'),
        ('drafts', 'Taslaklar'),
    ]
    
    email_account = models.ForeignKey(
        EmailAccount, 
        on_delete=models.CASCADE, 
        related_name='emails'
    )
    
    # Gmail tracking
    gmail_message_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    gmail_thread_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    # Sender/Recipients
    from_email = models.EmailField()
    from_name = models.CharField(max_length=200, blank=True)
    to_emails = ArrayField(models.EmailField(), default=list)
    cc_emails = ArrayField(models.EmailField(), default=list, blank=True)
    bcc_emails = ArrayField(models.EmailField(), default=list, blank=True)
    
    # Content
    subject = models.CharField(max_length=500)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    snippet = models.CharField(max_length=300, blank=True)  # Preview text
    
    # Folder & Status
    folder = models.CharField(max_length=20, choices=FOLDER_CHOICES, default='inbox', db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_starred = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    
    # CRM Connections - Auto-matched based on email address
    company = models.ForeignKey(
        'crm.Company', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='user_emails'
    )
    companies = models.ManyToManyField(
        'crm.Company',
        blank=True,
        related_name='user_emails_multi'
    )
    
    contact = models.ForeignKey(
        'crm.Contact', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='user_emails'
    )
    contacts = models.ManyToManyField(
        'crm.Contact',
        blank=True,
        related_name='user_emails_multi'
    )
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-received_at', '-sent_at', '-created_at']
        verbose_name = "Email"
        verbose_name_plural = "Emails"
        indexes = [
            models.Index(fields=['email_account', 'folder']),
            models.Index(fields=['company']),
            models.Index(fields=['contact']),
            models.Index(fields=['-sent_at']),
            models.Index(fields=['-received_at']),
        ]
    
    def __str__(self):
        return f"{self.subject[:50]} - {self.from_email}"
    
    def get_preview(self, max_length=150):
        """Get a preview of the email body"""
        text = self.body_text or self.snippet
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def match_crm_records(self):
        """Auto-match email to Company/Contact based on email addresses"""
        from crm.models import Company, Contact
        
        # Determine which email to match (from_email for inbox, to_emails for sent)
        emails_to_check = []
        if self.folder == 'inbox':
            emails_to_check = [self.from_email]
        elif self.folder == 'sent':
            emails_to_check = self.to_emails or []
        
        # Clear existing M2M (we'll re-add matches)
        # Note: We need to save first if object is new, but here it's likely existing.
        # If new, M2M operations might fail if PK is not set. Assuming PK is set.
        
        for email_addr in emails_to_check:
            if not email_addr:
                continue
            
            # Match Contacts (find ALL)
            matching_contacts = Contact.objects.filter(email__contains=[email_addr])
            for contact in matching_contacts:
                self.contacts.add(contact)
                # If contact belongs to a company, link that company too
                if contact.company:
                    self.companies.add(contact.company)
                
                # Legacy: Set first match as primary
                if not self.contact:
                    self.contact = contact
                if not self.company and contact.company:
                    self.company = contact.company
            
            # Match Companies directly (find ALL)
            matching_companies = Company.objects.filter(email__contains=[email_addr])
            for company in matching_companies:
                self.companies.add(company)
                
                # Legacy: Set first match as primary
                if not self.company:
                    self.company = company


class EmailAttachment(models.Model):
    """
    E-posta ekleri - Cloudinary'de saklanır.
    """
    email = models.ForeignKey(
        Email, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    
    filename = models.CharField(max_length=255)
    file_url = models.URLField(max_length=500)  # Cloudinary URL
    file_size = models.PositiveIntegerField(default=0)  # bytes
    content_type = models.CharField(max_length=100, blank=True)
    
    # Gmail attachment ID (for sync)
    gmail_attachment_id = models.TextField(blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Email Attachment"
        verbose_name_plural = "Email Attachments"
    
    def __str__(self):
        return f"{self.filename} ({self.get_size_display()})"
    
    def get_size_display(self):
        """Human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    def get_file_icon(self):
        """Return appropriate icon class based on content type"""
        content_type = self.content_type.lower()
        if 'pdf' in content_type:
            return 'fa-file-pdf'
        elif 'word' in content_type or 'document' in content_type:
            return 'fa-file-word'
        elif 'excel' in content_type or 'spreadsheet' in content_type:
            return 'fa-file-excel'
        elif 'image' in content_type:
            return 'fa-file-image'
        elif 'video' in content_type:
            return 'fa-file-video'
        elif 'zip' in content_type or 'rar' in content_type:
            return 'fa-file-archive'
        else:
            return 'fa-file'
