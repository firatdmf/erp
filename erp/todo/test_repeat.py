"""Repeating tasks: finishing one makes the next, by the schedule; deleting
one asks whether its series goes on.

Run with:
    python manage.py test todo.test_repeat
"""
import datetime

from django.contrib.auth.models import User
from django.test import Client, SimpleTestCase, TestCase

from authentication.models import Member
from team.models import Team, TeamBoardColumn, TeamMember
from todo.forms import TaskForm
from todo.models import Task
from todo.repeat import from_form, label, next_due

D = datetime.date


class WhenTheNextOneIsDue(SimpleTestCase):
    def test_monthly_on_the_first_stays_on_the_first(self):
        self.assertEqual(next_due(D(2026, 12, 1), "month", 1), D(2027, 1, 1))

    def test_the_31st_falls_back_in_short_months_and_returns_after(self):
        feb = next_due(D(2027, 1, 31), "month", 1, 31)
        self.assertEqual(feb, D(2027, 2, 28))
        self.assertEqual(next_due(feb, "month", 1, 31), D(2027, 3, 31))
        self.assertEqual(next_due(D(2027, 3, 31), "month", 1, 31), D(2027, 4, 30))

    def test_every_three_months(self):
        self.assertEqual(next_due(D(2026, 11, 15), "month", 3), D(2027, 2, 15))

    def test_yearly_from_the_29th_of_february(self):
        self.assertEqual(next_due(D(2028, 2, 29), "year", 1, 29), D(2029, 2, 28))

    def test_weekly(self):
        self.assertEqual(next_due(D(2026, 11, 14), "week", 2), D(2026, 11, 28))

    def test_labels(self):
        self.assertEqual(label("month", 1), "Every month")
        self.assertEqual(label("month", 3), "Every 3 months")
        self.assertEqual(label("", 1), "")

    def test_the_form_reads_unknown_as_no_repeat(self):
        self.assertEqual(from_form({"repeat_unit": "fortnight"}), ("", 1))
        self.assertEqual(from_form({"repeat_unit": "month", "repeat_every": "x"}), ("month", 1))
        self.assertEqual(from_form({"repeat_unit": "week", "repeat_every": "0"}), ("week", 1))


class RepeatingTasks(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("muhsin_repeat_test", password="pw", is_staff=True)
        self.me = Member.objects.get_or_create(user=self.user)[0]
        self.client = Client()
        self.client.force_login(self.user)

    def bill(self, **kw):
        fields = dict(name="Pay the business park fee", due_date=D(2026, 12, 1),
                      member=self.me, created_by=self.me, repeat_unit="month")
        fields.update(kw)
        return Task.objects.create(**fields)

    def tick(self, task, status="done"):
        return self.client.post(f"/todo/tasks/{task.pk}/complete_task", {"status": status},
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_finishing_makes_the_next_one_due_by_the_schedule(self):
        task = self.bill()
        task.assignees.set([self.me])
        self.tick(task)
        nxt = Task.objects.get(repeated_from=task)
        self.assertEqual(nxt.due_date, D(2027, 1, 1))
        self.assertEqual((nxt.name, nxt.member, nxt.repeat_unit, nxt.completed),
                         ("Pay the business park fee", self.me, "month", False))
        self.assertEqual(list(nxt.assignees.all()), [self.me])

    def test_ticked_late_the_next_one_keeps_its_date(self):
        # Paid on the 9th of December: January's is still due on the 1st.
        task = self.bill()
        self.tick(task)
        self.assertEqual(Task.objects.get(repeated_from=task).due_date, D(2027, 1, 1))

    def test_unticking_and_ticking_again_makes_one_next_task(self):
        task = self.bill()
        self.tick(task)
        self.tick(task, "todo")
        self.tick(task)
        self.assertEqual(Task.objects.filter(repeated_from=task).count(), 1)

    def test_an_open_task_makes_nothing(self):
        task = self.bill()
        self.tick(task, "in_progress")
        self.assertFalse(Task.objects.filter(repeated_from=task).exists())

    def test_finished_anywhere_counts_google_included(self):
        task = self.bill()
        task.set_status("done")  # what the Google sync does
        task.save()
        self.assertTrue(Task.objects.filter(repeated_from=task).exists())

    def test_a_task_that_does_not_repeat_makes_nothing(self):
        task = self.bill(repeat_unit="")
        self.tick(task)
        self.assertFalse(Task.objects.filter(repeated_from=task).exists())

    def test_the_series_remembers_its_day(self):
        task = self.bill(due_date=D(2027, 1, 31))
        self.assertEqual(task.repeat_day, 31)
        self.tick(task)
        feb = Task.objects.get(repeated_from=task)
        self.assertEqual((feb.due_date, feb.repeat_day), (D(2027, 2, 28), 31))
        self.tick(feb)
        self.assertEqual(Task.objects.get(repeated_from=feb).due_date, D(2027, 3, 31))

    def test_moving_the_due_date_moves_the_series_day(self):
        task = self.bill(due_date=D(2027, 1, 31))
        r = self.client.post(f"/todo/tasks/{task.pk}/update_ajax/", {
            "name": task.name, "due_date": "2027-01-15", "priority": "medium",
            "repeat_unit": "month", "repeat_every": "1"})
        self.assertTrue(r.json()["success"])
        task.refresh_from_db()
        self.assertEqual(task.repeat_day, 15)

    def test_the_edit_sidebar_sets_and_stops_repeating(self):
        task = self.bill(repeat_unit="")
        self.client.post(f"/todo/tasks/{task.pk}/update_ajax/", {
            "name": task.name, "due_date": "2026-12-01", "priority": "medium",
            "repeat_unit": "month", "repeat_every": "3"})
        task.refresh_from_db()
        self.assertEqual((task.repeat_unit, task.repeat_every), ("month", 3))
        self.client.post(f"/todo/tasks/{task.pk}/update_ajax/", {
            "name": task.name, "due_date": "2026-12-01", "priority": "medium",
            "repeat_unit": "", "repeat_every": "3"})
        task.refresh_from_db()
        self.assertEqual((task.repeat_unit, task.repeat_day), ("", None))

    def test_creating_with_repeat(self):
        r = self.client.post("/todo/tasks/create/", {
            "name": "SGK premium", "due_date": "2026-12-01", "priority": "high",
            "repeat_unit": "month", "repeat_every": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(r.json()["success"], r.content)
        self.assertEqual(Task.objects.get(name="SGK premium").repeat_label, "Every month")

    def test_a_form_without_the_repeat_field_keeps_the_schedule(self):
        task = self.bill()
        form = TaskForm({"name": "Renamed", "due_date": "2026-12-01", "priority": "medium"},
                        instance=task)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        task.refresh_from_db()
        self.assertEqual((task.name, task.repeat_unit), ("Renamed", "month"))

    def test_deleting_can_skip_just_this_one(self):
        task = self.bill()
        self.assertTrue(task.carries_series)
        self.client.post(f"/todo/tasks/{task.pk}/delete_task", {"keep_series": "1"},
                         HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())
        nxt = Task.objects.get(name="Pay the business park fee")
        self.assertEqual((nxt.due_date, nxt.repeat_unit), (D(2027, 1, 1), "month"))

    def test_deleting_otherwise_stops_the_series(self):
        task = self.bill()
        self.client.post(f"/todo/tasks/{task.pk}/delete_task",
                         HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(Task.objects.filter(name="Pay the business park fee").exists())

    def test_once_the_next_one_exists_the_series_no_longer_hangs_on_this_one(self):
        task = self.bill()
        self.tick(task)
        task.refresh_from_db()
        self.assertFalse(task.carries_series)
        self.assertTrue(Task.objects.get(repeated_from=task).carries_series)

    def test_the_list_marks_a_series_so_delete_asks(self):
        from todo.templatetags.todo_tags import tasks_component
        self.bill(due_date=D(2026, 1, 1))
        html = tasks_component("dictsort", "", "dashboard", None, None, "/", self.me)
        self.assertIn('data-repeat="Every month"', html)


class RepeatingTeamTasks(TestCase):
    def setUp(self):
        self.lead = User.objects.create_user("selin_repeat_test", password="pw")
        self.lead_m = Member.objects.get_or_create(user=self.lead)[0]
        self.team = Team.objects.create(name="Wharf crew", creator=self.lead)
        TeamMember.objects.create(team=self.team, user=self.lead, role="admin")
        self.todo_col = TeamBoardColumn.objects.create(team=self.team, title="To Do", order=0)
        self.done_col = TeamBoardColumn.objects.create(team=self.team, title="Done", order=3)
        self.client = Client()
        self.client.force_login(self.lead)

    def test_done_on_the_board_puts_the_next_one_in_to_do(self):
        r = self.client.post("/team/task/create/", {
            "team_id": self.team.pk, "name": "Weekly stock count", "due_date": "2026-11-16",
            "repeat_unit": "week", "repeat_every": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(r.json()["success"])
        task = Task.objects.get(name="Weekly stock count")
        self.client.post(f"/team/task/{task.pk}/status/", {"column_id": self.done_col.pk})
        nxt = Task.objects.get(repeated_from=task)
        self.assertEqual((nxt.team, nxt.due_date), (self.team, D(2026, 11, 23)))
        self.client.get(f"/team/tasks/?team_id={self.team.pk}")
        nxt.refresh_from_db()
        self.assertEqual(nxt.column, self.todo_col)

    def test_the_team_edit_form_sets_the_repeat(self):
        task = Task.objects.create(team=self.team, column=self.todo_col, name="Clean the dock",
                                   due_date=D(2026, 12, 1), created_by=self.lead_m)
        self.client.post(f"/team/task/{task.pk}/edit/", {
            "name": "Clean the dock", "due_date": "2026-12-01",
            "repeat_unit": "month", "repeat_every": "2"})
        task.refresh_from_db()
        self.assertEqual(task.repeat_label, "Every 2 months")

    def test_deleting_from_the_board_can_skip_just_this_one(self):
        task = Task.objects.create(team=self.team, column=self.todo_col, name="Clean the dock",
                                   due_date=D(2026, 12, 1), created_by=self.lead_m,
                                   repeat_unit="month")
        self.client.post(f"/team/task/{task.pk}/delete/", {"keep_series": "1"})
        self.assertEqual(Task.objects.get(name="Clean the dock").due_date, D(2027, 1, 1))
