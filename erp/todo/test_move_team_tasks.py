"""todo 0017: every team task moves into Task, with its people, comments
and history.

Run with:
    python manage.py test todo.test_move_team_tasks
"""
import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from erp.testing import TransactionTestCase

BEFORE = [("todo", "0016_task_team_and_column")]
AFTER = [("todo", "0017_move_team_tasks_into_task")]

UTC = datetime.timezone.utc


class TeamTasksMoveIntoTask(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(BEFORE)
        apps = executor.loader.project_state(BEFORE).apps
        User = apps.get_model("auth", "User")
        Member = apps.get_model("authentication", "Member")
        Team = apps.get_model("team", "Team")
        Column = apps.get_model("team", "TeamBoardColumn")
        TeamTask = apps.get_model("team", "TeamTask")
        Comment = apps.get_model("team", "TeamTaskComment")
        History = apps.get_model("team", "TeamTaskHistory")

        lead = User.objects.create(username="selin_move_test", first_name="Selin")
        doer = User.objects.create(username="emre_move_test", first_name="Emre")
        # A login nobody made a member: there is no one to carry over.
        guest = User.objects.create(username="guest_move_test")
        self.lead = Member.objects.create(user=lead).pk
        self.doer = Member.objects.create(user=doer).pk

        team = Team.objects.create(name="Wharf crew", creator=lead)
        done = Column.objects.create(team=team, title="Done", color="green", order=3)
        self.team, self.done = team.pk, done.pk

        created = datetime.datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
        finished = datetime.datetime(2026, 7, 9, 15, 0, tzinfo=UTC)
        old = TeamTask.objects.create(
            team=team, column=done, title="Pay the port fee",
            description="Before the ship leaves",
            assigned_by=lead, assigned_to=doer,
            status="done", priority="high",
            # 00:00 in Istanbul on 8 July, as every team task on prod is stored.
            due_date=datetime.datetime(2026, 7, 7, 21, 0, tzinfo=UTC),
            completed_at=finished, google_task_id="g-port-fee",
        )
        old.assignees.set([doer, guest])
        TeamTask.objects.filter(pk=old.pk).update(created_at=created)

        said = datetime.datetime(2026, 7, 2, 11, 0, tzinfo=UTC)
        c = Comment.objects.create(task=old, author=doer, content="Paid at the counter")
        Comment.objects.filter(pk=c.pk).update(created_at=said)
        Comment.objects.create(task=old, author=guest, content="Nobody to say this")
        History.objects.create(task=old, user=doer, event_type="status_change",
                               old_value="(Drag & Drop)", new_value="Done")
        History.objects.create(task=old, user=doer, event_type="comment_added",
                               new_value="Added a comment")
        self.created, self.finished, self.said = created, finished, said

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(AFTER)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _models(self, *names):
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state(AFTER).apps
        return [apps.get_model(*name.split(".")) for name in names]

    def test_the_task_keeps_what_it_was(self):
        (Task,) = self._models("todo.Task")
        task = Task.objects.get(team_id=self.team)
        self.assertEqual(task.name, "Pay the port fee")
        self.assertEqual(task.description, "Before the ship leaves")
        self.assertEqual(task.column_id, self.done)
        self.assertEqual((task.status, task.completed, task.priority), ("done", True, "high"))
        self.assertEqual(task.completed_at, self.finished)
        self.assertEqual(task.created_at, self.created)
        self.assertEqual(task.google_task_id, "g-port-fee")

    def test_the_due_day_is_the_day_in_istanbul(self):
        (Task,) = self._models("todo.Task")
        self.assertEqual(Task.objects.get(team_id=self.team).due_date, datetime.date(2026, 7, 8))

    def test_logins_become_their_members(self):
        (Task,) = self._models("todo.Task")
        task = Task.objects.get(team_id=self.team)
        self.assertEqual(task.created_by_id, self.lead)
        self.assertEqual(task.member_id, self.doer)
        # The login without a member is not carried.
        self.assertEqual(list(task.assignees.values_list("id", flat=True)), [self.doer])

    def test_comments_and_history_come_along(self):
        Task, TaskComment, TaskActivity = self._models(
            "todo.Task", "todo.TaskComment", "todo.TaskActivity")
        task = Task.objects.get(team_id=self.team)
        comments = list(TaskComment.objects.filter(task=task))
        self.assertEqual([(c.author_id, c.content) for c in comments],
                         [(self.doer, "Paid at the counter")])
        self.assertEqual(comments[0].created_at, self.said)
        self.assertEqual(
            sorted(TaskActivity.objects.filter(task=task).values_list("activity_type", "new_value")),
            [("comment_added", "Added a comment"), ("status_changed", "Done")])
