from django import template
from django.template.loader import render_to_string
from crm.models import Contact, Company
from django.utils import timezone
import datetime
import calendar
from django.conf import settings
# from django.utils.timezone import make_aware
import pytz
register = template.Library()


@register.simple_tag
def dashboard_component(csrf_token,path,member):
    import os as _osc, sys as _sysc
    print(f"\n>>> [TAG dashboard_component CALLED] PID={_osc.getpid()} member={member} __file__={__file__}", flush=True)

    # Below two lines result in the same thing but they give naive time warning so we fix it by setting the timezone
    # today = timezone.localtime(timezone.now()).date()
    # today = datetime.datetime.today().strftime('%Y-%m-%d')

    from todo.models import Task
    from team.models import TeamTask
    import json
    from collections import defaultdict
    from django.utils import timezone as django_timezone
    from django.db.models import Q
    from django.db.models.functions import TruncDate
    
    # ⚡ ULTRA FAST: Single aggregate query for all counts
    from django.db.models import Count, Q, Case, When, IntegerField
    from django.db.models.functions import TruncDate
    
    # Use the LOCAL date (settings.TIME_ZONE = Europe/Istanbul) — using
    # django_timezone.now().date() directly returns UTC, which slips a
    # day during the late-evening hours and breaks "today vs overdue"
    # bucketing.
    today_date = django_timezone.localtime(django_timezone.now()).date()
    
    # ⚡ Single query for today's leads (contacts + companies)
    from django.db.models import Sum
    number_of_leads_added = (
        Contact.objects.filter(created_at__date=today_date).count() +
        Company.objects.filter(created_at__date=today_date).count()
    )
    
    # ⚡ Single query for all task counts (using aggregate)
    if member:
        task_counts = Task.objects.filter(completed=False).aggregate(
            pending=Count('id'),
            my_tasks=Count('id', filter=Q(member=member) | Q(assignees=member), distinct=True),
            assigned=Count('id', filter=Q(created_by=member) & ~Q(member=member))
        )
        pending_tasks_count = task_counts['my_tasks']
        my_tasks_count = task_counts['my_tasks']
        assigned_tasks_count = task_counts['assigned']
        
        # Add TeamTask counts - tasks assigned to current user
        user = member.user if hasattr(member, 'user') else None
        if user:
            team_tasks_count = TeamTask.objects.filter(
                assignees=user
            ).exclude(status='done').distinct().count()
            my_tasks_count += team_tasks_count
            pending_tasks_count += team_tasks_count
    else:
        pending_tasks_count = Task.objects.filter(completed=False).count()
        my_tasks_count = 0
        assigned_tasks_count = 0
    
    # ⚡ Calendar data: Efficient grouping by date.
    # Show on the calendar EVERY task the current member is involved in:
    #   - personal tasks where they are the member OR in assignees
    #   - personal tasks they created (assigned to others)
    #   - team tasks assigned to them
    #   - team tasks they assigned to someone else
    #   - team meetings on their teams (added below)
    base_calendar_query = Task.objects.filter(completed=False)
    if member:
        base_calendar_query = base_calendar_query.filter(
            Q(member=member) | Q(assignees=member) | Q(created_by=member)
        ).distinct()

    tasks_by_date_query = base_calendar_query.annotate(
        date=TruncDate('due_date')
    ).values('date').annotate(
        count=Count('id', distinct=True)
    ).order_by('date')

    tasks_by_date = {
        item['date'].strftime('%Y-%m-%d'): item['count']
        for item in tasks_by_date_query if item['date']
    }

    # Add TeamTask to calendar data: assigned-to-me OR assigned-by-me
    if member and hasattr(member, 'user'):
        user = member.user
        # TeamTask.due_date is a DateTimeField — TruncDate would bucket
        # by UTC date and shift evening tasks to the next day. Pull the
        # rows and bucket in Python under the active local timezone so
        # the calendar matches what the user actually sees.
        from collections import Counter as _DateCounter
        _tz = django_timezone.get_current_timezone()
        team_task_due_dates = TeamTask.objects.filter(
            Q(assignees=user) | Q(assigned_by=user)
        ).exclude(status='done').values_list('id', 'due_date').distinct()

        _team_counter = _DateCounter()
        _seen_ids = set()
        for _id, _due in team_task_due_dates:
            if not _due or _id in _seen_ids:
                continue
            _seen_ids.add(_id)
            _local_date = django_timezone.localtime(_due, _tz).date()
            _team_counter[_local_date.strftime('%Y-%m-%d')] += 1

        for date_str, count in _team_counter.items():
            tasks_by_date[date_str] = tasks_by_date.get(date_str, 0) + count

    # Add Team Meetings to calendar data
    from team.models import TeamMeeting
    if member and hasattr(member, 'user'):
        # scheduled_at is DateTimeField — bucket in local TZ for the
        # same reason as TeamTask above.
        _tz_m = django_timezone.get_current_timezone()
        meeting_due = TeamMeeting.objects.filter(
            team__members=member.user,
            status__in=['scheduled', 'ongoing']
        ).values_list('id', 'scheduled_at').distinct()
        from collections import Counter as _MeetCounter
        _meet_counter = _MeetCounter()
        _meet_seen = set()
        for _mid, _scheduled in meeting_due:
            if not _scheduled or _mid in _meet_seen:
                continue
            _meet_seen.add(_mid)
            _local_d = django_timezone.localtime(_scheduled, _tz_m).date()
            _meet_counter[_local_d.strftime('%Y-%m-%d')] += 1
        for date_str, count in _meet_counter.items():
            tasks_by_date[date_str] = tasks_by_date.get(date_str, 0) + count
    
    tasks_calendar_data = json.dumps(dict(tasks_by_date))
    
    # Per-brand theme: Nejum profile uses dashboard_nejum.html which
    # mirrors the design kit's ScreenHome 1:1. Other tenants (e.g.
    # demfirat) keep dashboard_new.html — original layout untouched.
    from django.conf import settings as _dj_settings
    _theme = getattr(_dj_settings, 'UI_THEME', '')

    # ALL of this user's OPEN tasks for the Nejum dashboard. Completed
    # tasks are filtered out at the DB query so they never show up on
    # the calendar list view. Hand the full set to the client and let
    # JS slice by selected day. Demfirat path skips this work.
    all_tasks_by_date = {}
    today_tasks_data = []
    future_tasks_data = []
    delegated_tasks_data = []
    completed_tasks_data = []
    if _theme == 'nejum' and member:
        try:
            qs = (
                Task.objects
                .filter(member=member, completed=False)
                .select_related('company', 'contact', 'supplier', 'member__user')
                .order_by('-due_date', 'priority', 'id')[:200]
            )

            # ─── DEBUG: log per-task contact/company so we can compare 8000 vs 8001 ───
            import sys as _sys, socket as _sock, os as _os
            from django.conf import settings as _set
            from django import get_version as _gv
            _LOG = lambda m: print(m, flush=True)
            _LOG(f"\n{'='*60}")
            _LOG(f"🐍 [HOME DASHBOARD] PID={_os.getpid()} Python={_sys.version.split()[0]} Django={_gv()}")
            _LOG(f"   __file__={__file__}")
            _LOG(f"   THEME={_theme} BRAND={getattr(_set, 'BRAND', '?')} SCHEMA={getattr(_set, 'DB_SCHEMA', '?')}")
            _LOG(f"   DB.NAME={_set.DATABASES['default'].get('NAME')} HOST={_set.DATABASES['default'].get('HOST')}")
            _LOG(f"   Member={member} (id={getattr(member, 'id', '?')})")
            tasks_eval = list(qs)
            _LOG(f"   My open tasks: {len(tasks_eval)}")
            for _t in tasks_eval[:30]:
                cn = getattr(getattr(_t, 'contact', None), 'name', None) if _t.contact_id else None
                co = getattr(getattr(_t, 'company', None), 'name', None) if _t.company_id else None
                _LOG(f"   • Task#{_t.id} {_t.name!r} contact_id={_t.contact_id}({cn!r}) company_id={_t.company_id}({co!r})")
            _LOG(f"{'='*60}\n")
            qs = tasks_eval  # use the already-evaluated list for the loop below

            # Delegated = tasks where the user is in `assignees` but not
            # the owner (`member`). Captures "tasks others assigned to me".
            # NOTE: distinct() must come BEFORE the slice — calling it
            # on a sliced QuerySet raises TypeError, which previously
            # got swallowed by the surrounding except and cleared every
            # other list.
            delegated_qs = (
                Task.objects
                .filter(assignees=member, completed=False)
                .exclude(member=member)
                .select_related('company', 'contact', 'supplier', 'member__user')
                .distinct()
                .order_by('-due_date', 'priority', 'id')[:200]
            )
            for t in qs:
                age_days = (today_date - t.due_date).days
                if age_days >= 14:
                    aging = {'label': f'{age_days}d', 'tone': 'red'}
                elif age_days >= 1:
                    aging = {'label': f'{age_days}d', 'tone': 'amber'}
                elif age_days == 0:
                    aging = {'label': 'Today', 'tone': 'green'}
                elif age_days == -1:
                    aging = {'label': 'Tomorrow', 'tone': 'green'}
                else:
                    aging = {'label': f'in {abs(age_days)}d', 'tone': 'amber'}
                assignee = t.member.user.first_name if (t.member and t.member.user and t.member.user.first_name) else (t.member.user.username if (t.member and t.member.user) else '?')
                # Linked entity (company / contact / supplier) — show whichever is set
                entity_name = ''
                entity_type = ''
                if t.company_id and t.company:
                    entity_name = getattr(t.company, 'name', '') or str(t.company)
                    entity_type = 'company'
                elif t.contact_id and t.contact:
                    entity_name = getattr(t.contact, 'name', '') or str(t.contact)
                    entity_type = 'contact'
                elif t.supplier_id and t.supplier:
                    entity_name = (
                        getattr(t.supplier, 'company_name', '')
                        or getattr(t.supplier, 'contact_name', '')
                        or str(t.supplier)
                    )
                    entity_type = 'supplier'
                # User can edit the task if they're the creator, assignee,
                # or a superuser. Tasks with no creator (legacy) are editable.
                _can_edit = bool(
                    (not t.created_by)
                    or (member and t.created_by == member)
                    or (member and t.member == member)
                    or (getattr(member, 'user', None) and getattr(member.user, 'is_superuser', False))
                )
                # Delete is broader than edit: creator, single assignee,
                # any m2m assignee, or superuser/staff may remove.
                _user = getattr(member, 'user', None) if member else None
                _can_delete = t.can_be_deleted_by(_user) if _user else False
                payload = {
                    'id': t.id,
                    'name': t.name,
                    'priority': (t.priority or 'medium'),
                    'date_label': t.due_date.strftime('%d.%m.%Y'),
                    # ISO date string for client-side sorting/grouping
                    'date_iso': t.due_date.isoformat(),
                    'aging_label': aging['label'],
                    'aging_tone': aging['tone'],
                    'assignee': assignee,
                    'avatar_letter': (assignee[:1] or '?').upper(),
                    'completed': bool(t.completed),
                    'entity_name': entity_name,
                    'entity_type': entity_type,
                    'can_edit': _can_edit,
                    'can_delete': _can_delete,
                    'kind': 'personal',
                }
                key = t.due_date.isoformat()  # YYYY-MM-DD
                all_tasks_by_date.setdefault(key, []).append(payload)
                # Initial server-rendered list = today's open + every
                # still-open earlier (overdue) task. Mirrors the JS
                # default landing view so the page paints right away.
                # Future tasks are excluded by design.
                if t.due_date <= today_date:
                    today_tasks_data.append(payload)
                else:
                    future_tasks_data.append(payload)

            # Sort the initial list to match the JS default order:
            # today's tasks first (priority high→low), then overdue
            # newest-past first. Server-side rendering paints the same
            # order JS would render right after hydration.
            _prio = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
            _today_iso = today_date.isoformat()
            today_tasks_data.sort(key=lambda p: (
                0 if p['date_iso'] == _today_iso else 1,    # today first
                -int(''.join(p['date_iso'].split('-')))      # newer past before older past
                  if p['date_iso'] != _today_iso else 0,
                _prio.get(p['priority'], 9),                  # priority within day
            ))

            # Completed tasks the user is involved in (member, assignee,
            # or creator). Limited to the most recent 100 — older items
            # are still in the database but the dashboard list is meant
            # to be a short review, not an archive.
            from django.db.models import Q as _Q_cmpl
            try:
                completed_qs = (
                    Task.objects
                    .filter(completed=True)
                    .filter(
                        _Q_cmpl(member=member)
                        | _Q_cmpl(assignees=member)
                        | _Q_cmpl(created_by=member)
                    )
                    .select_related('company', 'contact', 'supplier', 'member__user')
                    .distinct()
                    .order_by('-completed_at', '-due_date', 'id')[:100]
                )
                _user_for_can = getattr(member, 'user', None) if member else None
                for t in completed_qs:
                    # Linked entity (company / contact / supplier)
                    c_entity_name = ''
                    c_entity_type = ''
                    if t.company_id and t.company:
                        c_entity_name = getattr(t.company, 'name', '') or str(t.company)
                        c_entity_type = 'company'
                    elif t.contact_id and t.contact:
                        c_entity_name = getattr(t.contact, 'name', '') or str(t.contact)
                        c_entity_type = 'contact'
                    elif t.supplier_id and t.supplier:
                        c_entity_name = (
                            getattr(t.supplier, 'company_name', '')
                            or getattr(t.supplier, 'contact_name', '')
                            or str(t.supplier)
                        )
                        c_entity_type = 'supplier'
                    c_assignee = (
                        t.member.user.first_name
                        if (t.member and t.member.user and t.member.user.first_name)
                        else (t.member.user.username if (t.member and t.member.user) else '?')
                    )
                    completed_label = ''
                    if t.completed_at:
                        completed_label = t.completed_at.strftime('%d.%m.%Y')
                    completed_tasks_data.append({
                        'id': t.id,
                        'name': t.name,
                        'priority': (t.priority or 'medium'),
                        'date_label': t.due_date.strftime('%d.%m.%Y') if t.due_date else '',
                        'date_iso': t.due_date.isoformat() if t.due_date else '',
                        'completed_at': completed_label,
                        'completed_at_iso': t.completed_at.isoformat() if t.completed_at else '',
                        'assignee': c_assignee,
                        'avatar_letter': (c_assignee[:1] or '?').upper(),
                        'completed': True,
                        'entity_name': c_entity_name,
                        'entity_type': c_entity_type,
                        'can_delete': t.can_be_deleted_by(_user_for_can) if _user_for_can else False,
                        'kind': 'personal',
                    })
            except Exception as _cmpl_err:
                import traceback as _tb_c
                print(f"[dashboard_component] completed task fetch failed: {_cmpl_err}")
                _tb_c.print_exc()

            # Delegated tasks payload — same shape so the existing
            # task-card template works without branching.
            for t in delegated_qs:
                age_days = (today_date - t.due_date).days
                if age_days >= 14:
                    aging = {'label': f'{age_days}d', 'tone': 'red'}
                elif age_days >= 1:
                    aging = {'label': f'{age_days}d', 'tone': 'amber'}
                elif age_days == 0:
                    aging = {'label': 'Today', 'tone': 'green'}
                elif age_days == -1:
                    aging = {'label': 'Tomorrow', 'tone': 'green'}
                else:
                    aging = {'label': f'in {abs(age_days)}d', 'tone': 'amber'}
                # Show the original owner as the "from" person on the card
                owner = t.member.user.first_name if (t.member and t.member.user and t.member.user.first_name) else (t.member.user.username if (t.member and t.member.user) else '?')
                entity_name = ''
                entity_type = ''
                if t.company_id and t.company:
                    entity_name = getattr(t.company, 'name', '') or str(t.company)
                    entity_type = 'company'
                elif t.contact_id and t.contact:
                    entity_name = getattr(t.contact, 'name', '') or str(t.contact)
                    entity_type = 'contact'
                elif t.supplier_id and t.supplier:
                    entity_name = (
                        getattr(t.supplier, 'company_name', '')
                        or getattr(t.supplier, 'contact_name', '')
                        or str(t.supplier)
                    )
                    entity_type = 'supplier'
                _can_edit_d = bool(
                    (not t.created_by)
                    or (member and t.created_by == member)
                    or (member and t.member == member)
                    or (getattr(member, 'user', None) and getattr(member.user, 'is_superuser', False))
                )
                _user_d = getattr(member, 'user', None) if member else None
                _can_delete_d = t.can_be_deleted_by(_user_d) if _user_d else False
                _payload_d = {
                    'id': t.id,
                    'name': t.name,
                    'can_edit': _can_edit_d,
                    'can_delete': _can_delete_d,
                    'priority': (t.priority or 'medium'),
                    'date_label': t.due_date.strftime('%d.%m.%Y'),
                    'date_iso': t.due_date.isoformat(),
                    'aging_label': aging['label'],
                    'aging_tone': aging['tone'],
                    'assignee': owner,  # who delegated it to me
                    'avatar_letter': (owner[:1] or '?').upper(),
                    'completed': bool(t.completed),
                    'entity_name': entity_name,
                    'entity_type': entity_type,
                    'kind': 'personal',
                }
                delegated_tasks_data.append(_payload_d)
                if t.due_date > today_date:
                    future_tasks_data.append(_payload_d)
            # ─── Team tasks ────────────────────────────────────────────
            # The Nejum dashboard cards must show team tasks alongside
            # personal ones. We include team tasks where the user is in
            # `assignees` OR is the one who `assigned_by` it. Each gets
            # marked `kind: 'team'` so the card renders the team badge
            # and the JS routes delete to /team/task/<id>/delete/.
            try:
                _user = getattr(member, 'user', None)
                if _user:
                    from team.models import TeamMember
                    team_qs = (
                        TeamTask.objects
                        .filter(Q(assignees=_user) | Q(assigned_by=_user))
                        .exclude(status='done')
                        .select_related('team', 'assigned_by')
                        .distinct()
                        .order_by('-due_date', 'priority', 'id')[:200]
                    )
                    # Which teams does the user have admin/manager/owner role in?
                    # Used to gate the trash icon — matches team.views.delete_task.
                    _mgmt_team_ids = set(
                        TeamMember.objects
                        .filter(user=_user, role__in=['admin', 'manager', 'owner'])
                        .values_list('team_id', flat=True)
                    )
                    for tt in team_qs:
                        # TeamTask.due_date is a DateTimeField stored in
                        # UTC. Convert to local time before calling
                        # .date() — otherwise an evening-hours task in
                        # Istanbul slips to the next UTC day and lands
                        # on the wrong calendar cell.
                        if tt.due_date:
                            tt_date = django_timezone.localtime(tt.due_date).date()
                        else:
                            tt_date = today_date
                        age_days = (today_date - tt_date).days
                        if age_days >= 14:
                            tt_aging = {'label': f'{age_days}d', 'tone': 'red'}
                        elif age_days >= 1:
                            tt_aging = {'label': f'{age_days}d', 'tone': 'amber'}
                        elif age_days == 0:
                            tt_aging = {'label': 'Today', 'tone': 'green'}
                        elif age_days == -1:
                            tt_aging = {'label': 'Tomorrow', 'tone': 'green'}
                        else:
                            tt_aging = {'label': f'in {abs(age_days)}d', 'tone': 'amber'}
                        # "Assignee" line shows who assigned the task to
                        # me, or the user's own name if I'm the delegator.
                        if tt.assigned_by_id == _user.id:
                            tt_assignee = (
                                _user.first_name
                                or _user.username
                                or '?'
                            )
                        elif tt.assigned_by:
                            tt_assignee = (
                                tt.assigned_by.first_name
                                or tt.assigned_by.username
                                or '?'
                            )
                        else:
                            tt_assignee = '?'
                        tt_can_delete = bool(
                            tt.assigned_by_id == _user.id
                            or _user.is_superuser
                            or _user.is_staff
                            or tt.team_id in _mgmt_team_ids
                        )
                        tt_payload = {
                            'id': tt.id,
                            'name': tt.title,
                            'priority': (tt.priority or 'medium'),
                            'date_label': tt_date.strftime('%d.%m.%Y'),
                            'date_iso': tt_date.isoformat(),
                            'aging_label': tt_aging['label'],
                            'aging_tone': tt_aging['tone'],
                            'assignee': tt_assignee,
                            'avatar_letter': (tt_assignee[:1] or '?').upper(),
                            'completed': (tt.status == 'done'),
                            'entity_name': tt.team.name if tt.team else '',
                            'entity_type': 'team',
                            'can_edit': True,   # team-task edit goes through team UI
                            'can_delete': tt_can_delete,
                            'kind': 'team',     # routes delete URL on the client
                        }
                        key = tt_date.isoformat()
                        all_tasks_by_date.setdefault(key, []).append(tt_payload)
                        if tt_date <= today_date:
                            today_tasks_data.append(tt_payload)
                        else:
                            future_tasks_data.append(tt_payload)
                        # Tasks others assigned to me also show on the
                        # "Assigned Tasks" tab — only if I'm not the
                        # delegator.
                        if tt.assigned_by_id != _user.id:
                            delegated_tasks_data.append(tt_payload)
            except Exception as _team_err:
                import traceback as _tb2
                print(f"[dashboard_component] team-task fetch failed: {_team_err}")
                _tb2.print_exc()

            # Re-sort the merged list now that team tasks are in it.
            _prio2 = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
            _today_iso2 = today_date.isoformat()
            today_tasks_data.sort(key=lambda p: (
                0 if p['date_iso'] == _today_iso2 else 1,
                -int(''.join(p['date_iso'].split('-')))
                  if p['date_iso'] != _today_iso2 else 0,
                _prio2.get(p['priority'], 9),
            ))

            # Sort future tasks chronologically by due date ascending, then priority
            _prio_f = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
            future_tasks_data.sort(key=lambda p: (
                p['date_iso'],
                _prio_f.get(p['priority'], 9)
            ))
        except Exception as _e:
            # Surface the cause instead of silently swallowing it —
            # last time this hid a slice-then-distinct bug for a while.
            import traceback as _tb
            print(f"[dashboard_component] task fetch failed: {_e}")
            _tb.print_exc()
            today_tasks_data = []
            all_tasks_by_date = {}
            delegated_tasks_data = []

    template = (
        'components/dashboard_nejum.html' if _theme == 'nejum'
        else 'components/dashboard_new.html'
    )
    return render_to_string(template, {
        'csrf_token':csrf_token,
        'number_of_leads_added':number_of_leads_added,
        'pending_tasks_count':pending_tasks_count,
        'my_tasks_count':my_tasks_count,
        'assigned_tasks_count':assigned_tasks_count,
        'tasks_calendar_data':tasks_calendar_data,
        'today_tasks':today_tasks_data,
        'today_date':today_date,
        # JSON dict { 'YYYY-MM-DD': [ {task...}, ... ] } consumed by
        # the Nejum dashboard JS for day-by-day filtering.
        'tasks_by_date_json': json.dumps(all_tasks_by_date),
        # Tasks assigned TO me by others (TeamTask-lite via Task.assignees)
        'delegated_tasks_json': json.dumps(delegated_tasks_data),
        'assigned_tasks_count': len(delegated_tasks_data),
        # Tasks the user has completed (or were completed under them),
        # for the "Completed" dashboard tab with bulk-delete checkboxes.
        'completed_tasks_json': json.dumps(completed_tasks_data),
        'completed_tasks_count': len(completed_tasks_data),
        # Future tasks for the Task Reports view
        'future_tasks_json': json.dumps(future_tasks_data),
        'future_tasks_count': len(future_tasks_data),
        # 'country_of_the_day':country_of_the_day,
        'path':path,
        'member':member,
    })

@register.simple_tag
def test_component(csrf_token):
    return render_to_string('components/test_component.html',{'context':"This is the test page context","csrf_token":csrf_token})

@register.simple_tag
def search_component(csrf_token):
    return render_to_string('components/search_component.html',{'context':"This is the test page context","csrf_token":csrf_token})