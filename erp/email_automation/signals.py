from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from crm.models import Company
from .models import EmailCampaign, EmailTemplate


@receiver(post_save, sender=Company)
def create_campaign_for_prospect(sender, instance, created, **kwargs):
    """
    Automatically create email campaign when a company is created with 'prospect' status
    """
    # Only create campaign for new prospect companies that have an email address
    if created and instance.status == 'prospect':
        # Check if company has email address
        if not instance.email or instance.email.strip() == '':
            print(f"⊘ Skipping campaign creation for {instance.name} - no email address")
            return
        
        # Check if user has email templates set up
        user = instance.created_by if hasattr(instance, 'created_by') else None
        
        # For now, we'll use the first user who has templates
        # In production, you'd want to assign campaigns to specific users
        if not user:
            # Try to find a user with templates
            from django.contrib.auth.models import User
            users_with_templates = User.objects.filter(email_templates__isnull=False).distinct()
            if users_with_templates.exists():
                user = users_with_templates.first()
        
        if user:
            # Check if campaign already exists
            if not hasattr(instance, 'email_campaign'):
                # Get first template to determine initial schedule
                first_template = EmailTemplate.objects.filter(
                    user=user,
                    sequence_number=1,
                    is_active=True
                ).first()
                
                if first_template:
                    # Create campaign
                    campaign = EmailCampaign.objects.create(
                        company=instance,
                        user=user,
                        status='active',
                        emails_sent=0,
                        next_email_scheduled_at=timezone.now()  # Email 1 sends immediately!
                    )
                    print(f"✓ Campaign created for {instance.name}")
                    
                    # Send Email 1 immediately
                    from .email_service import send_campaign_email
                    try:
                        if send_campaign_email(campaign, sequence_number=1):
                            print(f"✓ Email 1 sent immediately to {instance.name}")
                        else:
                            print(f"✗ Failed to send Email 1 to {instance.name}")
                    except Exception as e:
                        print(f"✗ Error sending Email 1: {str(e)}")


@receiver(pre_save, sender=Company)
def check_status_change(sender, instance, **kwargs):
    """
    Pause or stop campaign when company status changes from prospect
    """
    if instance.pk:  # Only for existing companies
        try:
            old_instance = Company.objects.get(pk=instance.pk)
            
            # If status changed from prospect to something else
            if old_instance.status == 'prospect' and instance.status != 'prospect':
                try:
                    campaign = instance.email_campaign
                    if campaign.status == 'active':
                        campaign.status = 'paused'
                        campaign.save()
                        print(f"✓ Campaign paused for {instance.name} - status changed to {instance.status}")
                except EmailCampaign.DoesNotExist:
                    pass
        except Company.DoesNotExist:
            pass
