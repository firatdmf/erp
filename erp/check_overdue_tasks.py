import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
os.environ['BRAND'] = 'belino'
django.setup()

from todo.models import Task
from authentication.models import Member
from django.utils import timezone

today = timezone.localdate()
print(f'Today: {today}')

m = Member.objects.get(id=1)
print(f'Member: {m}')

# Tasks with company that are overdue or today (what shows on initial load)
overdue_with_co = Task.objects.filter(
    member=m, completed=False,
    company__isnull=False,
    due_date__lte=today
).select_related('company').order_by('due_date')

print(f'\nOverdue/Today tasks WITH company: {overdue_with_co.count()}')
for t in overdue_with_co:
    print(f'  Task {t.id}: {t.name!r} | due={t.due_date} | company={t.company.name}')

# All overdue/today tasks
overdue_all = Task.objects.filter(
    member=m, completed=False,
    due_date__lte=today
).order_by('due_date')

print(f'\nAll overdue/today tasks: {overdue_all.count()}')
for t in overdue_all:
    co = t.company.name if t.company_id and t.company else 'No company'
    print(f'  Task {t.id}: {t.name!r} | due={t.due_date} | {co}')
