"""An admin reaches every team without being put in it; anyone else only
the teams they are in. See team/access.py."""
from django.contrib.auth.models import User
from django.test import Client, TestCase

from authentication.models import Member, Permission
from team.models import ChatRoom, Team, TeamMember


class TeamAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("ruzana_team_test", password="pw-for-test")
        self.team = Team.objects.create(name="Zircon Squad", creator=self.owner)
        TeamMember.objects.create(team=self.team, user=self.owner, role="member")
        ChatRoom.objects.create(team=self.team, name="General", room_type="channel",
                                created_by=self.owner, is_default=True)

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def test_an_admin_sees_and_opens_a_team_they_are_not_in(self):
        boss = User.objects.create_superuser("boss_team_test", password="pw-for-test")
        client = self.client_for(boss)
        self.assertContains(client.get("/team/members/"), "Zircon Squad")
        for path in (f"/team/tasks/?team_id={self.team.pk}",
                     f"/team/messages/?team_id={self.team.pk}",
                     f"/team/roles/?team_id={self.team.pk}"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)
        self.assertEqual(client.get("/team/manageable/").json()["teams"],
                         [{"id": self.team.pk, "name": "Zircon Squad"}])
        # Reaching it does not put them on its roster.
        self.assertFalse(TeamMember.objects.filter(team=self.team, user=boss).exists())

    def test_anyone_else_reaches_only_their_own_teams(self):
        # A middle manager included: a team belongs to the install, not a book.
        outsider = User.objects.create_user("burak_team_test", password="pw-for-test")
        Member.objects.get_or_create(user=outsider)[0].permissions.add(
            Permission.objects.get_or_create(name="middle_manager")[0])
        client = self.client_for(outsider)
        self.assertNotContains(client.get("/team/members/"), "Zircon Squad")
        self.assertEqual(client.get(f"/team/tasks/?team_id={self.team.pk}").status_code, 404)
        self.assertEqual(client.get(f"/team/messages/?team_id={self.team.pk}").status_code, 404)

    def test_a_member_still_reaches_their_team(self):
        client = self.client_for(self.owner)
        self.assertEqual(client.get(f"/team/tasks/?team_id={self.team.pk}").status_code, 200)
