from django.contrib import admin
from .models import EmailAccount, EmailTemplate, EmailCampaign, SentEmail, ReceivedEmail


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ['email_address', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email_address', 'user__username']
    readonly_fields = ['access_token', 'refresh_token', 'token_expiry', 'created_at', 'updated_at']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['sequence_number', 'name', 'user', 'days_after_previous', 'is_active']
    list_filter = ['sequence_number', 'is_active', 'user']
    search_fields = ['name', 'subject']
    ordering = ['user', 'sequence_number']


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['company', 'user', 'status', 'emails_sent', 'last_email_sent_at', 'reply_received']
    list_filter = ['status', 'reply_received', 'user']
    search_fields = ['company__name', 'user__username']
    readonly_fields = ['emails_sent', 'last_email_sent_at', 'reply_received_at', 'created_at', 'updated_at']


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'campaign', 'sent_at', 'replied']
    list_filter = ['replied', 'opened', 'sent_at']
    search_fields = ['recipient_email', 'recipient_name', 'subject', 'campaign__company__name']
    readonly_fields = ['sent_at', 'gmail_message_id', 'gmail_thread_id']
    date_hierarchy = 'sent_at'


@admin.register(ReceivedEmail)
class ReceivedEmailAdmin(admin.ModelAdmin):
    list_display = ['sender_email', 'subject', 'campaign', 'received_at', 'is_reply', 'processed']
    list_filter = ['is_reply', 'processed', 'received_at']
    search_fields = ['sender_email', 'sender_name', 'subject']
    readonly_fields = ['gmail_message_id', 'gmail_thread_id', 'received_at', 'created_at']
    date_hierarchy = 'received_at'
