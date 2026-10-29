"""Roles: who holds which permissions, set a role at a time.

Every check in the app reads Member.permissions. A role does not add a
second place to look: it writes its permissions onto each of its members,
here, whenever a member joins it or its permissions change — so a member in
a role has exactly the role's permissions, and nothing else changes for
the code that asks.
"""
from django.db import transaction

from .models import ACCESS_LEVEL_CHOICES_DICT, Member, Permission, Role


def permission_row(name):
    """The Permission row for `name`, made the first time it is used."""
    return Permission.objects.get_or_create(
        name=name, defaults={"description": ACCESS_LEVEL_CHOICES_DICT[name][1]})[0]


@transaction.atomic
def put_in_role(member, role):
    """Move `member` into `role`: from now on they have exactly its
    permissions."""
    member.role = role
    member.save(update_fields=["role"])
    member.permissions.set(role.permissions.all())


@transaction.atomic
def set_role_permission(role, name, granted):
    """Give `role` the permission `name`, or take it away, and with it
    every member in the role."""
    perm = permission_row(name)
    if granted:
        role.permissions.add(perm)
    else:
        role.permissions.remove(perm)
    for member in role.members.all():
        if granted:
            member.permissions.add(perm)
        else:
            member.permissions.remove(perm)


def board():
    """What Settings → Members & permissions shows: every role with its
    permissions and members, the members in no role yet, and the
    superusers, who may do everything whatever role they are in.

    {"permissions": [(name, label, description)],
     "roles": [{role, granted: [(name, label, description, held)], members: [...]}],
     "unplaced": [member], "superusers": [member]}
    """
    permissions = [(name, label, description)
                   for name, (label, description) in ACCESS_LEVEL_CHOICES_DICT.items()]
    members = list(Member.objects.filter(user__isnull=False, user__is_active=True)
                   .select_related("user", "role").prefetch_related("books", "permissions")
                   .order_by("user__username"))
    for member in members:
        member.display_name = member.user.get_full_name() or member.user.username
        member.book_names = ", ".join(b.name for b in member.books.all())
        member.held = [label for name, label, _d in permissions
                       if name in {p.name for p in member.permissions.all()}]
    roles = []
    for role in Role.objects.prefetch_related("permissions"):
        held = {p.name for p in role.permissions.all()}
        roles.append({
            "role": role,
            "granted": [(name, label, desc, name in held) for name, label, desc in permissions],
            "members": [m for m in members if m.role_id == role.pk and not m.user.is_superuser],
        })
    return {
        "permissions": permissions,
        "roles": roles,
        "unplaced": [m for m in members if m.role_id is None and not m.user.is_superuser],
        "superusers": [m for m in members if m.user.is_superuser],
    }
