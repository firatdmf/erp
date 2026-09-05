"""Who made this record, and who is allowed to change it.

Two halves that belong together:

  * `stamp_creator` records the acting user on a row the first time it
    is saved. It is wired as a pre_save receiver rather than set in each
    view, because a record here can be born down several paths — the
    order form, the inline "quick create customer" on that form, an
    import, a JSON API — and a rule that each view has to remember is a
    rule that some view will forget. The user comes from the same
    thread-local the order audit trail uses
    (operating.audit.CurrentUserMiddleware), so it works in any of them
    and is simply left NULL outside a request (a shell script, a
    migration, a cron job).

  * `can_edit` answers whether someone may change a record they are
    looking at: admins may change anything, everyone else may change
    only what they made themselves.

Rows created before the `created_by` column existed have NULL there.
Those are treated as ADMIN-ONLY: nobody can claim authorship of a row
whose author was never recorded, so the safe reading of "no creator" is
"not yours". Say so out loud, because the opposite default — treating
an unowned row as everyone's — would quietly open every historical
record to every user the moment this shipped.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver


def stamp_creator(sender, instance, **kwargs):
    """pre_save: record who is creating this row, once, at insert."""
    # `_state.adding` is True only before the first INSERT, so an edit
    # never rewrites the original author.
    if not instance._state.adding:
        return
    if getattr(instance, "created_by_id", None) is not None:
        return
    try:
        from operating.audit import get_current_user

        user = get_current_user()
    except Exception:
        return
    if user is not None:
        instance.created_by = user


def register(*models):
    """Wire stamp_creator for each model, keyed so it registers once."""
    for model in models:
        pre_save.connect(
            stamp_creator,
            sender=model,
            dispatch_uid=f"stamp_creator:{model._meta.label_lower}",
        )


def is_admin(user):
    """Django superuser/staff, or a Member carrying 'admin'.

    Mirrors operating.views_warehouse._is_admin; kept here so this
    module does not drag the warehouse views into every import.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        return user.member.permissions.filter(name="admin").exists()
    except Exception:
        return False


def can_edit(user, obj):
    """May `user` change `obj`? Admins always; otherwise its creator.

    A record whose `created_by` is NULL — anything predating the column
    — is admin-only, so an unowned row is never treated as everyone's.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if is_admin(user):
        return True
    creator_id = getattr(obj, "created_by_id", None)
    if creator_id is None:
        return False
    return creator_id == user.pk
