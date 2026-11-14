"""A team task is a Task with a team: the board creates, moves, edits,
comments on and deletes Task rows, and the dashboard lists them with the
personal ones.

Run with:
    python manage.py test team.test_team_tasks
"""
import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from authentication.models import Member
from team.models import Team, TeamBoardColumn, TeamMember
from todo.models import Task, TaskActivity, TaskComment


class TeamTaskIsATask(TestCase):
    def setUp(self):
        self.lead = User.objects.create_user("selin_board_test", password="pw", first_name="Selin")
        self.doer = User.objects.create_user("emre_board_test", password="pw", first_name="Emre")
        self.lead_m = Member.objects.get_or_create(user=self.lead)[0]
        self.doer_m = Member.objects.get_or_create(user=self.doer)[0]
        self.team = Team.objects.create(name="Wharf crew", creator=self.lead)
        TeamMember.objects.create(team=self.team, user=self.lead, role="admin")
        TeamMember.objects.create(team=self.team, user=self.doer, role="member")
        self.todo_col = TeamBoardColumn.objects.create(team=self.team, title="To Do", order=0)
        self.done_col = TeamBoardColumn.objects.create(team=self.team, title="Done", color="green", order=3)

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def make_task(self, **kw):
        task = Task.objects.create(
            team=self.team, column=self.todo_col, name=kw.get("name", "Pay the port fee"),
            due_date=kw.get("due_date", timezone.localdate()),
            created_by=self.lead_m, member=self.doer_m)
        task.assignees.set([self.doer_m])
        return task

    def test_creating_on_the_board_makes_a_task_with_the_team(self):
        r = self.client_for(self.lead).post("/team/task/create/", {
            "team_id": self.team.pk, "name": "Book the truck", "due_date": "2026-12-01",
            "priority": "high", "assigned_users": str(self.doer.pk),
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(r.json()["success"])
        task = Task.objects.get(name="Book the truck")
        self.assertEqual((task.team, task.column), (self.team, self.todo_col))
        self.assertEqual(task.due_date, datetime.date(2026, 12, 1))
        self.assertEqual((task.created_by, task.member), (self.lead_m, self.doer_m))
        self.assertEqual(list(task.assignees.all()), [self.doer_m])
        self.assertFalse(task.completed)

    def test_a_task_without_a_date_is_due_today(self):
        self.client_for(self.lead).post("/team/task/create/", {
            "team_id": self.team.pk, "name": "Sweep the dock"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(Task.objects.get(name="Sweep the dock").due_date, timezone.localdate())

    def test_the_board_lists_the_teams_tasks(self):
        self.make_task()
        r = self.client_for(self.doer).get(f"/team/tasks/?team_id={self.team.pk}")
        self.assertContains(r, "Pay the port fee")

    def test_moving_to_done_finishes_the_task_like_anywhere_else(self):
        task = self.make_task()
        r = self.client_for(self.doer).post(f"/team/task/{task.pk}/status/",
                                            {"column_id": self.done_col.pk})
        self.assertTrue(r.json()["success"])
        task.refresh_from_db()
        self.assertEqual((task.status, task.completed, task.column), ("done", True, self.done_col))
        self.assertIsNotNone(task.completed_at)
        self.assertTrue(TaskActivity.objects.filter(
            task=task, activity_type="status_changed", new_value="Done").exists())

        # And back out of Done reopens it.
        self.client_for(self.doer).post(f"/team/task/{task.pk}/status/",
                                        {"column_id": self.todo_col.pk})
        task.refresh_from_db()
        self.assertEqual((task.status, task.completed, task.completed_at), ("todo", False, None))

    def test_editing_records_what_changed_and_keeps_the_date_when_left_blank(self):
        task = self.make_task(due_date=datetime.date(2026, 12, 1))
        r = self.client_for(self.lead).post(f"/team/task/{task.pk}/edit/", {
            "name": "Pay the port fee twice", "due_date": "", "priority": "medium"})
        self.assertTrue(r.json()["success"])
        task.refresh_from_db()
        self.assertEqual(task.name, "Pay the port fee twice")
        self.assertEqual(task.due_date, datetime.date(2026, 12, 1))
        self.assertTrue(TaskActivity.objects.filter(
            task=task, activity_type="name_updated", old_value="Pay the port fee").exists())

    def test_comments_are_task_comments_and_show_on_the_page(self):
        task = self.make_task()
        self.client_for(self.doer).post(f"/team/task/{task.pk}/add_comment/",
                                        {"content": "Paid at the counter"})
        comment = TaskComment.objects.get(task=task)
        self.assertEqual(comment.author, self.doer_m)
        page = self.client_for(self.lead).get(f"/team/task/{task.pk}/")
        self.assertContains(page, "Paid at the counter")
        self.assertContains(page, "added a comment")

    def test_only_the_creator_or_a_team_manager_deletes(self):
        task = self.make_task()
        self.assertEqual(self.client_for(self.doer).post(f"/team/task/{task.pk}/delete/").status_code, 403)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        self.assertTrue(self.client_for(self.lead).post(f"/team/task/{task.pk}/delete/").json()["success"])
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_a_personal_task_is_not_reachable_through_the_team_pages(self):
        personal = Task.objects.create(name="Call the bank", due_date=timezone.localdate(),
                                       created_by=self.lead_m, member=self.lead_m)
        self.assertEqual(self.client_for(self.lead).get(f"/team/task/{personal.pk}/").status_code, 404)

    def test_each_task_opens_on_its_own_page(self):
        task = self.make_task()
        personal = Task.objects.create(name="Call the bank", due_date=timezone.localdate(),
                                       member=self.lead_m)
        self.assertEqual(task.get_absolute_url(), f"/team/task/{task.pk}/")
        self.assertEqual(personal.get_absolute_url(), f"/todo/tasks/{personal.pk}/detail/")

    def test_the_dashboard_lists_a_team_task_once_with_its_team(self):
        import json, re
        from erp.templatetags.erp_tags import dashboard_component
        self.make_task(name="Pay the port fee")
        html = dashboard_component("", "/", self.doer_m)
        by_date = json.loads(re.search(r"var tasksByDate = (\{.*?\});", html).group(1))
        listed = [t for day in by_date.values() for t in day if t["name"] == "Pay the port fee"]
        self.assertEqual(len(listed), 1, "listed once, not as personal and team")
        self.assertEqual((listed[0]["kind"], listed[0]["entity_name"]), ("team", "Wharf crew"))

    def test_google_hears_which_team_a_task_is_from(self):
        from todo.google_tasks import _google_body
        body = _google_body(self.make_task())
        self.assertTrue(body["notes"].startswith("[ERP Team Task from Wharf crew]"))
        self.assertEqual(body["title"], "Pay the port fee")
