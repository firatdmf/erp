from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Company, CompanyFollowUp
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Company)
def create_followup_for_prospect(sender, instance, created, **kwargs):
    """
    Create a CompanyFollowUp record when a new Company is created with 'prospect' status.
    Email sending is now handled in the view to avoid database connection issues.
    """
    # Only create follow-up tracking if explicitly enabled
    # Email sending is now handled in CompanyCreate view
    pass


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
