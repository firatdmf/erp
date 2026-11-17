from django.db import models

# Create your models here.
from django.utils import timezone
from django.urls import reverse
from crm.models import Contact, Company, LinkedRecordManager

# from authentication.models import Member
from datetime import datetime, date
from authentication.models import Member



class TaskAttachment(models.Model):
    """Files attached to personal tasks (stored in Google Drive)"""
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255)
    drive_file_id = models.CharField(max_length=255)
    drive_link = models.URLField(max_length=500)
    uploaded_by = models.ForeignKey(Member, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

    def get_download_url(self):
        """Returns direct download link"""
        return f"https://drive.google.com/uc?export=download&id={self.drive_file_id}"


class Task(models.Model):
    # blank=True: This parameter specifies whether the field is allowed to be blank in forms
    # null=True: This parameter specifies whether the field is allowed to have a null value in the database. If null=True, the field will be nullable in the database, meaning it can have a value of NULL. It applies to the database schema. Setting null=True means that the field can be empty in the database, but it may still be required in forms unless blank=True is also set.
    # So, in summary:
    # blank=True affects form validation.
    # null=True affects the database schema.
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('done', 'Done'),
    ]

    name = models.CharField(max_length=200)
    due_date = models.DateField(db_index=True)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', db_index=True)
    completed = models.BooleanField(default=False, db_index=True)
    on_hold = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    google_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of the task in Google Tasks")

    # Repeating: every `repeat_every` weeks, months or years (todo/repeat.py).
    # Finishing the task makes the next one; `repeat_day` is the day of the
    # month the series was set for, and `repeated_from` the task this one
    # came after — one next task per task, so ticking twice makes one.
    REPEAT_CHOICES = [
        ('', 'Never'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year'),
    ]
    repeat_unit = models.CharField(max_length=10, choices=REPEAT_CHOICES, blank=True, default='')
    repeat_every = models.PositiveSmallIntegerField(default=1)
    repeat_day = models.PositiveSmallIntegerField(blank=True, null=True)
    repeated_from = models.OneToOneField(
        'self', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='next_in_series',
    )
    # make it either a company or a contact
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    # A team task is a task with a team: it shows on that team's board, in
    # the column it sits in. There is one kind of task — personal and team
    # tasks repeat, sync to Google and keep history the same way — and
    # these two fields are all that sets a team's tasks apart.
    team = models.ForeignKey(
        'team.Team', on_delete=models.CASCADE, blank=True, null=True,
        related_name='tasks',
    )
    column = models.ForeignKey(
        'team.TeamBoardColumn', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='tasks',
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True, related_name='assigned_tasks')
    assignees = models.ManyToManyField(Member, related_name='tasks', blank=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_tasks')

    # A task names the customer it is about wherever it is listed, so one
    # about another directory's customer is left out — see
    # crm.models.LinkedRecordManager. `everywhere` is unwalled.
    objects = LinkedRecordManager("contact", "company")
    everywhere = models.Manager()

    def __str__(self):
        if self.company:
            return f"{self.name} for | {self.company}"
        elif self.contact:
            return f"{self.name} for | {self.contact}"
        else:
            return self.name

    #  Add a delete_url field to your Todo model to store the URL that will be used to delete the todo item.
    #  You can use the reverse function to generate this URL.
    def get_delete_url(self):
        return reverse("complete_task", args=[str(self.id)])

    def get_absolute_url(self):
        """A team task opens on its team's pages, any other on To-do's."""
        if self.team_id:
            return reverse("team:task_detail", args=[self.pk])
        return reverse("todo:task_detail", kwargs={"task_id": self.pk})

    def set_status(self, status):
        """Move the task to `status` and keep `completed` / `completed_at`
        in step with it. Every place that finishes or reopens a task goes
        through here, so done means the same thing on every screen.
        The caller saves."""
        self.status = status
        if status == 'done':
            self.completed = True
            self.on_hold = False
            if not self.completed_at:
                self.completed_at = timezone.now()
        else:
            self.completed = False
            self.on_hold = False
            self.completed_at = None

    class Meta:
        indexes = [
            models.Index(fields=['completed', 'due_date']),
            models.Index(fields=['due_date', 'completed']),
            models.Index(fields=['priority', 'completed']),
            # ⚡ SEARCH OPTIMIZATION INDEXES
            models.Index(fields=['member', 'completed', 'priority', 'due_date']),  # My Tasks query
            models.Index(fields=['created_by', 'completed', 'member']),  # Delegated tasks query
            models.Index(fields=['name']),  # Search by name
        ]
        ordering = ['-priority', 'due_date']
        
    def save(self, *args, **kwargs):
        if not self.member and hasattr(self, "_current_member"):
            self.member = self._current_member
        # A series remembers the day of the month it was set for; an edit
        # that moves the due date clears it here to set it afresh.
        if self.repeat_unit:
            if not self.repeat_day and self.due_date:
                self.repeat_day = self.due_date.day
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'repeat_day'}
        else:
            self.repeat_day = None
        super().save(*args, **kwargs)
        # Finished, wherever that happened: the series comes round again.
        if self.completed and self.repeat_unit:
            self.make_next()

    def set_repeat(self, unit, every):
        """Give the task a schedule ('' = none) from the Repeat field."""
        if unit != self.repeat_unit:
            self.repeat_day = None
        self.repeat_unit, self.repeat_every = unit, every

    def set_due_date(self, due):
        """Move the due date; a series then keeps the new day of the month."""
        if due != self.due_date:
            self.repeat_day = None
        self.due_date = due

    @property
    def repeat_label(self):
        """'Every month' — empty for a task that does not repeat."""
        from .repeat import label
        return label(self.repeat_unit, self.repeat_every)

    @property
    def carries_series(self):
        """Whether the series hangs on this task: it repeats and its next
        one is not made yet. Deleting it ends the series unless the next
        one is made first (make_next)."""
        if not self.repeat_unit or not self.pk:
            return False
        return not Task.everywhere.filter(repeated_from=self).exists()

    def delete_from_series(self, keep_series=False):
        """Delete the task. With `keep_series`, its series goes on: the next
        one is made first, as if this one were done ("skip just this one").
        Without, a series that hangs on this task ends with it."""
        if keep_series:
            self.make_next()
        self.delete()

    def make_next(self):
        """Make the task after this one in its series, if it repeats and
        that task is not made already. Returns the next task, or None."""
        from django.db import IntegrityError, transaction
        from .repeat import next_due

        if not self.repeat_unit or not self.pk:
            return None
        existing = Task.everywhere.filter(repeated_from=self).first()
        if existing:
            return existing
        try:
            with transaction.atomic():
                nxt = Task.everywhere.create(
                    name=self.name,
                    description=self.description,
                    priority=self.priority,
                    due_date=next_due(self.due_date, self.repeat_unit,
                                      self.repeat_every, self.repeat_day),
                    contact=self.contact,
                    company=self.company,
                    team=self.team,
                    # No column: the board puts an open task in To Do.
                    member=self.member,
                    created_by=self.created_by,
                    repeat_unit=self.repeat_unit,
                    repeat_every=self.repeat_every,
                    repeat_day=self.repeat_day,
                    repeated_from=self,
                )
                nxt.assignees.set(self.assignees.all())
        except IntegrityError:
            # Made by a save running at the same moment.
            return Task.everywhere.filter(repeated_from=self).first()

        def push():
            owner = self.member or self.created_by
            if owner is None or owner.user is None:
                return
            try:
                from .google_tasks import push_task_to_google
                push_task_to_google(owner.user, nxt)
            except Exception as e:
                print(f"Error pushing the next repeating task to Google Tasks: {e}")
        transaction.on_commit(push)
        return nxt
    
    def get_priority_color(self):
        """Return color for priority badge"""
        colors = {
            'low': '#10b981',      # green
            'medium': '#f59e0b',   # orange
            'high': '#ef4444',     # red
            'urgent': '#dc2626',   # dark red
        }
        return colors.get(self.priority, '#6b7280')
    
    def get_priority_icon(self):
        """Return icon for priority"""
        icons = {
            'low': 'fa-arrow-down',
            'medium': 'fa-minus',
            'high': 'fa-arrow-up',
            'urgent': 'fa-exclamation-triangle',
        }
        return icons.get(self.priority, 'fa-minus')

    def can_be_deleted_by(self, user):
        """
        Return True if the given Django ``User`` is allowed to delete this task.

        Rule of thumb:
        - Superusers / staff can always delete.
        - The creator (created_by) can delete.
        - The single assigned member (member) can delete their own task.
        - A user in the m2m assignees set can delete.
        - Tasks someone else assigned to me that I'm NOT in any of those roles
          for return False — I see the task but cannot remove it.
        """
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        member = getattr(user, "member", None)
        if not member:
            return False
        if self.created_by_id == member.id:
            return True
        if self.member_id == member.id:
            return True
        if self.team_id:
            # A team's admins and managers look after its board.
            from team.access import has_team_role
            if has_team_role(user, self.team):
                return True
        # m2m check
        return self.assignees.filter(pk=member.id).exists()


class TaskComment(models.Model):
    """Comments on tasks for collaboration"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.task.name}"


class TaskActivity(models.Model):
    """Activity log for task changes"""
    ACTIVITY_TYPES = [
        ('created', 'Task Created'),
        ('completed', 'Task Completed'),
        ('reopened', 'Task Reopened'),
        ('priority_changed', 'Priority Changed'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned To'),
        ('due_date_changed', 'Due Date Changed'),
        ('description_updated', 'Description Updated'),
        ('name_updated', 'Name Updated'),
        ('comment_added', 'Comment Added'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='task_activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Task Activities'
        indexes = [
            models.Index(fields=['task', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.task.name}"
    
    def get_icon(self):
        """Return icon for activity type"""
        icons = {
            'created': 'fa-plus-circle',
            'completed': 'fa-check-circle',
            'reopened': 'fa-undo',
            'priority_changed': 'fa-flag',
            'status_changed': 'fa-sync-alt',
            'assigned': 'fa-user-plus',
            'due_date_changed': 'fa-calendar-alt',
            'description_updated': 'fa-align-left',
            'name_updated': 'fa-edit',
            'comment_added': 'fa-comment',
        }
        return icons.get(self.activity_type, 'fa-circle')
    
    def get_color(self):
        """Return color for activity type"""
        colors = {
            'created': '#10b981',      # green
            'completed': '#10b981',    # green
            'reopened': '#f59e0b',     # orange
            'priority_changed': '#8b5cf6',  # purple
            'status_changed': '#3b82f6',    # blue
            'assigned': '#6366f1',     # indigo
            'due_date_changed': '#f97316',  # orange
            'description_updated': '#64748b',  # gray
            'name_updated': '#64748b',  # gray
        }
        return colors.get(self.activity_type, '#64748b')
