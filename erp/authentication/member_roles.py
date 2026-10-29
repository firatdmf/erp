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
from django.utils.translation import gettext as _

from .models import ACCESS_LEVEL_CHOICES_DICT, GRANTS, RESTRICTIONS, Member, Permission, Role

# The board's name for the superusers' card: not a Role row but Django's
# own superuser flag, which reaches every book and everything else.
SUPERADMIN = "superadmin"


class Refused(Exception):
    """A move the board will not make, with the reason to show."""


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
def make_superadmin(member):
    """Make `member` a superadmin: Django's superuser (and staff, for its
    admin), who may do everything in every book. Their role no longer
    applies, so they leave it."""
    user = member.user
    user.is_superuser = user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])
    member.role = None
    member.save(update_fields=["role"])


@transaction.atomic
def leave_superadmin(member, role, by):
    """Take `member` out of the superadmins, into `role`.

    Refused for oneself — one wrong drag would lock a superadmin out of the
    board they would need to undo it — and for the last superadmin, since
    someone has to be able to run the install.
    """
    from django.contrib.auth.models import User

    user = member.user
    if user.pk == by.pk:
        raise Refused(_("You can't take yourself out of Superadmin."))
    if not User.objects.filter(is_active=True, is_superuser=True).exclude(pk=user.pk).exists():
        raise Refused(_("The last superadmin can't be moved out."))
    user.is_superuser = user.is_staff = False
    user.save(update_fields=["is_superuser", "is_staff"])
    put_in_role(member, role)


@transaction.atomic
def set_member_book(member, book, assigned):
    """Let `member` work in `book`, or no longer. A member whose working
    book is taken away works in the next one they still have."""
    if assigned:
        member.books.add(book)
        if member.default_book_id is None:
            member.default_book = book
            member.save(update_fields=["default_book"])
        return
    member.books.remove(book)
    if member.default_book_id == book.pk:
        member.default_book = member.books.order_by("pk").first()
        member.save(update_fields=["default_book"])


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


def dress(member, books):
    """Put on `member` what their card shows: name, the books they work in
    (each of `books`, ticked or not), and — in no role yet — the
    permissions they hold."""
    member.display_name = member.user.get_full_name() or member.user.username
    mine = {b.pk for b in member.books.all()}
    member.book_choices = [(b, b.pk in mine) for b in books]
    held = {p.name for p in member.permissions.all()}
    member.held = [label for name, label, _d in grant_list() if name in held]
    return member


def board():
    """What Settings → Members & permissions shows: the superadmins first,
    every role with its permissions and members, and the members in no
    role yet — each person with the books they work in."""
    from accounting.models import Book

    books = list(Book.objects.order_by("pk"))
    members = [dress(m, books) for m in
               Member.objects.filter(user__isnull=False, user__is_active=True)
               .select_related("user", "role").prefetch_related("books", "permissions")
               .order_by("user__username")]
    superadmins = [m for m in members if m.user.is_superuser]
    roles = [role_card(role, [m for m in members
                              if m.role_id == role.pk and not m.user.is_superuser])
             for role in Role.objects.prefetch_related("permissions")]
    return {
        "grants": grant_list(),
        "superadmin": {"members": superadmins,
                       "granted": [(n, l, d, True) for n, l, d in grant_list()]},
        "roles": roles,
        "unplaced": [m for m in members if m.role_id is None and not m.user.is_superuser],
        "books": books,
    }
