"""Move every team.TeamTask into todo.Task, with its comments, files and
history, so there is one kind of task.

A team task becomes a Task with that team and board column. Its people
were user logins; a Task's are members, matched through Member.user.
`title` becomes `name`. Its due date was a date and time and becomes the
day it falls on in the install's time zone (Europe/Istanbul): every team
task on prod was due at 00:00 Istanbul, stored as 21:00 UTC the day
before, and reading the UTC date would move each one back a day.

Created, completed and comment times are kept as they were. The old rows
stay where they are, unread, until a later release drops their tables.

Data only, in its own migration: the columns it fills were added in 0016.
"""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import migrations


EVENT_TO_ACTIVITY = {
    "status_change": "status_changed",
    "comment_added": "comment_added",
    "priority_change": "priority_changed",
    "created": "created",
}


def move_team_tasks(apps, schema_editor):
    TeamTask = apps.get_model("team", "TeamTask")
    TeamTaskComment = apps.get_model("team", "TeamTaskComment")
    TeamTaskAttachment = apps.get_model("team", "TeamTaskAttachment")
    TeamTaskHistory = apps.get_model("team", "TeamTaskHistory")
    Task = apps.get_model("todo", "Task")
    TaskComment = apps.get_model("todo", "TaskComment")
    TaskAttachment = apps.get_model("todo", "TaskAttachment")
    TaskActivity = apps.get_model("todo", "TaskActivity")
    Member = apps.get_model("authentication", "Member")

    member_of_user = dict(
        Member.objects.exclude(user=None).values_list("user_id", "id"))
    tz = ZoneInfo(settings.TIME_ZONE)

    for old in TeamTask.objects.order_by("id"):
        status = "done" if old.status in ("done", "completed") else old.status
        due = old.due_date.astimezone(tz).date() if old.due_date else old.created_at.astimezone(tz).date()
        task = Task.objects.create(
            name=old.title,
            description=old.description or "",
            team_id=old.team_id,
            column_id=old.column_id,
            due_date=due,
            priority=old.priority,
            status=status,
            completed=(status == "done"),
            completed_at=old.completed_at if status == "done" else None,
            created_by_id=member_of_user.get(old.assigned_by_id),
            member_id=member_of_user.get(old.assigned_to_id),
            google_task_id=old.google_task_id,
        )
        Task.objects.filter(pk=task.pk).update(created_at=old.created_at)

        assignee_ids = [member_of_user[u] for u in old.assignees.values_list("id", flat=True)
                        if u in member_of_user]
        if assignee_ids:
            task.assignees.set(assignee_ids)

        for c in TeamTaskComment.objects.filter(task=old).order_by("id"):
            author = member_of_user.get(c.author_id)
            if author is None:
                continue
            new = TaskComment.objects.create(task=task, author_id=author, content=c.content)
            TaskComment.objects.filter(pk=new.pk).update(
                created_at=c.created_at, updated_at=c.created_at)

        for a in TeamTaskAttachment.objects.filter(task=old).order_by("id"):
            uploader = member_of_user.get(a.uploaded_by_id)
            if uploader is None:
                continue
            new = TaskAttachment.objects.create(
                task=task, file_name=a.file_name, drive_file_id=a.drive_file_id,
                drive_link=a.drive_link, uploaded_by_id=uploader)
            TaskAttachment.objects.filter(pk=new.pk).update(created_at=a.created_at)

        for h in TeamTaskHistory.objects.filter(task=old).order_by("id"):
            new = TaskActivity.objects.create(
                task=task,
                user_id=member_of_user.get(h.user_id),
                activity_type=EVENT_TO_ACTIVITY.get(h.event_type, "status_changed"),
                old_value=h.old_value,
                new_value=h.new_value,
            )
            TaskActivity.objects.filter(pk=new.pk).update(created_at=h.created_at)


def remove_moved_tasks(apps, schema_editor):
    """Undo: the moved copies are the only tasks with a team, and the
    originals were never touched."""
    Task = apps.get_model("todo", "Task")
    Task.objects.exclude(team=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("todo", "0016_task_team_and_column"),
        ("authentication", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_team_tasks, remove_moved_tasks),
    ]
