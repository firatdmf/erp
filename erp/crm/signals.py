from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Company, CompanyFollowUp
from .email_utils import send_followup_email
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Company)
def create_followup_for_prospect(sender, instance, created, **kwargs):
    """
    Create a CompanyFollowUp record when a new Company is created with 'prospect' status.
    Sends the first email immediately.
    """
    if created and instance.status == "prospect" and instance.email:
        # Create follow-up tracking
        followup = CompanyFollowUp.objects.create(company=instance)
        
        # Send the first email immediately
        logger.info(f"Sending initial email to {instance.name} ({instance.email})")
        success = send_followup_email(instance, email_number=1)
        
        if success:
            # Mark the first email as sent
            followup.mark_email_sent()
            logger.info(f"Initial email sent successfully to {instance.name}")
        else:
            logger.error(f"Failed to send initial email to {instance.name}")


@receiver(pre_save, sender=Company)
def stop_followup_on_status_change(sender, instance, **kwargs):
    """
    Stop follow-up emails when company status changes from 'prospect' to anything else.
    """
    if instance.pk:  # Only for existing companies
        try:
            old_instance = Company.objects.get(pk=instance.pk)
            
            # Check if status is changing from 'prospect' to something else
            if old_instance.status == "prospect" and instance.status != "prospect":
                try:
                    followup = instance.followup
                    if followup.is_active:
                        followup.stop_followups(reason="status_changed")
                except CompanyFollowUp.DoesNotExist:
                    # No follow-up exists, nothing to stop
                    pass
        except Company.DoesNotExist:
            pass
