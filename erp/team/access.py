"""Who may reach a team, and what they may do in it.

A team's members, by their role in it — and the install's admins
(erp.ownership.is_install_admin), who reach every team as its admin
without being put in it. Admins oversee every team, and a team they had
to be a member of to see would carry them on its roster, its task
assignment list and its chat's member list for no reason but access.

Install admins only, not Member 'admin' or a middle manager: a team
belongs to the install, not to a book, so a branch's manager does not
read another team's chat.
"""
from erp.ownership import is_install_admin

from .models import Team, TeamMember

MANAGING_ROLES = ("admin", "manager", "owner")


def teams_for(user):
    """Every team `user` may open: all of them for an admin."""
    if is_install_admin(user):
        return Team.objects.all()
    return user.teams.all()


def is_team_member(user, team):
    return (is_install_admin(user)
            or TeamMember.objects.filter(team=team, user=user).exists())


def has_team_role(user, team, roles=MANAGING_ROLES):
    """Whether `user` holds one of `roles` in `team` — always, for an admin."""
    return (is_install_admin(user)
            or TeamMember.objects.filter(team=team, user=user, role__in=roles).exists())


def team_role(user, team):
    """`user`'s role in `team`: "admin" for an admin who is not in it,
    None for anyone else who is not."""
    member = TeamMember.objects.filter(team=team, user=user).first()
    if member is not None:
        return member.role
    return "admin" if is_install_admin(user) else None


def managed_team_ids(user):
    """Ids of the teams where `user` may manage tasks."""
    if is_install_admin(user):
        return set(Team.objects.values_list("id", flat=True))
    return set(TeamMember.objects
               .filter(user=user, role__in=MANAGING_ROLES)
               .values_list("team_id", flat=True))
