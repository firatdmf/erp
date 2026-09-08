from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from .models import Attachment, Company, CompanyFollowUp
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


@receiver(post_delete, sender=Attachment)
def remove_attachment_bytes(sender, instance, **kwargs):
    """Take the file with the row.

    On the signal rather than in the delete view because most
    attachments will not die by that route: deleting a contact cascades
    its rows away, and without this the documents would sit in the
    storage zone forever, belonging to a record that no longer exists.

    A storage error is logged, not raised — the row is already gone by
    the time this runs, and refusing to finish the delete would leave
    the database in a worse state than an orphaned file does.
    """
    if instance.path:
        try:
            from marketing.utils.bunny_storage import delete_from_bunny
            delete_from_bunny(instance.path)
        except Exception:
            logger.exception(
                "Could not remove attachment %s (%s) from Bunny",
                instance.pk, instance.path)
    elif instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:
            logger.exception(
                "Could not remove the local copy of attachment %s", instance.pk)
