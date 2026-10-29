"""Roles: who holds which permissions, set a role at a time.

Every check in the app reads Member.permissions. A role does not add a
second place to look: it writes onto each of its members, whenever they
join it or its permissions change, exactly what it grants — plus the
restriction each grant it lacks stands for (RESTRICTIONS): no Orders, no
orders shown; no Beyond sales, selling only. So a role is only ever a set
of permissions, and Sales rep or Operations manager is just a role that
leaves one out.
"""
from django.db import transaction

from .models import ACCESS_LEVEL_CHOICES_DICT, GRANTS, RESTRICTIONS, Member, Permission, Role


def permission_row(name):
    """The Permission row for `name`, made the first time it is used."""
    return Permission.objects.get_or_create(
        name=name, defaults={"description": ACCESS_LEVEL_CHOICES_DICT[name][1]})[0]


def held_by(role):
    """What a member of `role` holds: its grants, and the restriction of
    every grant it leaves out."""
    granted = {p.name for p in role.permissions.all()} & set(GRANTS)
    restricted = {flag for flag, grant in RESTRICTIONS.items() if grant not in granted}
    return [permission_row(name) for name in sorted(granted | restricted)]


@transaction.atomic
def put_in_role(member, role):
    """Move `member` into `role`: from now on they hold exactly what it
    gives."""
    member.role = role
    member.save(update_fields=["role"])
    member.permissions.set(held_by(role))


@transaction.atomic
def set_role_permission(role, name, granted):
    """Give `role` the permission `name`, or take it away, and with it
    every member in the role."""
    if granted:
        role.permissions.add(permission_row(name))
    else:
        role.permissions.remove(permission_row(name))
    held = held_by(role)
    for member in role.members.all():
        member.permissions.set(held)


def grant_list():
    """[(name, label, description)] of what a role can be given."""
    return [(name, *ACCESS_LEVEL_CHOICES_DICT[name]) for name in GRANTS]


def role_card(role, members=()):
    """One role as the board draws it."""
    held = {p.name for p in role.permissions.all()}
    return {
        "role": role,
        "granted": [(name, label, desc, name in held) for name, label, desc in grant_list()],
        "members": list(members),
    }


def board():
    """What Settings → Members & permissions shows: every role with its
    permissions and members, the members in no role yet, and the
    superusers, who may do everything whatever role they are in."""
    members = list(Member.objects.filter(user__isnull=False, user__is_active=True)
                   .select_related("user", "role").prefetch_related("books", "permissions")
                   .order_by("user__username"))
    for member in members:
        member.display_name = member.user.get_full_name() or member.user.username
        member.book_names = ", ".join(b.name for b in member.books.all())
        held = {p.name for p in member.permissions.all()}
        member.held = [label for name, label, _d in grant_list() if name in held]
    roles = [role_card(role, [m for m in members
                              if m.role_id == role.pk and not m.user.is_superuser])
             for role in Role.objects.prefetch_related("permissions")]
    return {
        "grants": grant_list(),
        "roles": roles,
        "unplaced": [m for m in members if m.role_id is None and not m.user.is_superuser],
        "superusers": [m for m in members if m.user.is_superuser],
    }
