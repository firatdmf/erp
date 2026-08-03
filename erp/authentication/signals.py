from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Member


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_member_for_user(sender, instance, created, **kwargs):
    """Every Django User gets a matching Member on create.

    The task/team pickers and permission checks (see views_warehouse._is_admin)
    all go through Member. Creating a User via `create_user`, the admin, or
    any other path without also making a Member left the account unpickable
    in those UIs — this signal removes that footgun.
    """
    if created:
        Member.objects.get_or_create(user=instance)
