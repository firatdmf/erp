import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
os.environ['BRAND'] = 'belino'
django.setup()

from todo.models import Task
from authentication.models import Member

m = Member.objects.get(id=5)
print('Member:', m)
tasks = Task.objects.filter(member=m, completed=False).select_related('company', 'contact').order_by('due_date')[:10]
for t in tasks:
    co = t.company.name if t.company else 'None'
    ct = t.contact.name if t.contact else 'None'
    print(f'Task {t.id}: {repr(t.name)} | company_id={t.company_id} | Company: {co} | Contact: {ct}')
