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
    
    # ⚡ Calendar data: Efficient grouping by date
    base_calendar_query = Task.objects.filter(completed=False)
    if member:
        base_calendar_query = base_calendar_query.filter(Q(member=member) | Q(assignees=member)).distinct()

    tasks_by_date_query = base_calendar_query.annotate(
        date=TruncDate('due_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Convert to dict
    tasks_by_date = {
        item['date'].strftime('%Y-%m-%d'): item['count']
        for item in tasks_by_date_query if item['date']
    }
    
    # Add TeamTask to calendar data
    if member and hasattr(member, 'user'):
        team_tasks_by_date = TeamTask.objects.filter(
            assignees=member.user
        ).exclude(status='done').annotate(
            date=TruncDate('due_date')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        for item in team_tasks_by_date:
            if item['date']:
                date_str = item['date'].strftime('%Y-%m-%d')
                if date_str in tasks_by_date:
                    tasks_by_date[date_str] += item['count']
                else:
                    tasks_by_date[date_str] = item['count']

    # Add Team Meetings to calendar data
    from team.models import TeamMeeting
    if member and hasattr(member, 'user'):
        meetings_by_date = TeamMeeting.objects.filter(
            team__members=member.user, # User must be a member of the team
            status__in=['scheduled', 'ongoing']
        ).annotate(
            date=TruncDate('scheduled_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        for item in meetings_by_date:
            if item['date']:
                date_str = item['date'].strftime('%Y-%m-%d')
                if date_str in tasks_by_date:
                    tasks_by_date[date_str] += item['count']
                else:
                    tasks_by_date[date_str] = item['count']
    
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
    delegated_tasks_data = []
    if _theme == 'nejum' and member:
        try:
            qs = (
                Task.objects
                .filter(member=member, completed=False)
                .select_related('company', 'contact', 'member__user')
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
                .select_related('company', 'contact', 'member__user')
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
                # Linked entity (company / contact) — show whichever is set
                entity_name = ''
                entity_type = ''
                if t.company_id and t.company:
                    entity_name = getattr(t.company, 'name', '') or str(t.company)
                    entity_type = 'company'
                elif t.contact_id and t.contact:
                    entity_name = getattr(t.contact, 'name', '') or str(t.contact)
                    entity_type = 'contact'
                # User can edit the task if they're the creator, assignee,
                # or a superuser. Tasks with no creator (legacy) are editable.
                _can_edit = bool(
                    (not t.created_by)
                    or (member and t.created_by == member)
                    or (member and t.member == member)
                    or (getattr(member, 'user', None) and getattr(member.user, 'is_superuser', False))
                )
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
                }
                key = t.due_date.isoformat()  # YYYY-MM-DD
                all_tasks_by_date.setdefault(key, []).append(payload)
                # Initial server-rendered list = today's open + every
                # still-open earlier (overdue) task. Mirrors the JS
                # default landing view so the page paints right away.
                # Future tasks are excluded by design.
                if t.due_date <= today_date:
                    today_tasks_data.append(payload)

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
                _can_edit_d = bool(
                    (not t.created_by)
                    or (member and t.created_by == member)
                    or (member and t.member == member)
                    or (getattr(member, 'user', None) and getattr(member.user, 'is_superuser', False))
                )
                delegated_tasks_data.append({
                    'id': t.id,
                    'name': t.name,
                    'can_edit': _can_edit_d,
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
                })
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