import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
os.environ['BRAND'] = 'belino'
django.setup()

from authentication.models import Member
from erp.templatetags.erp_tags import dashboard_component

m = Member.objects.get(id=1)
html = dashboard_component('test_csrf', '/', m)

# Check for entity chips in the rendered HTML
import re
entity_spans = re.findall(r'task-entity[^"]*"[^>]*>.*?</span>', html, re.DOTALL)
print(f'Entity spans found: {len(entity_spans)}')
for span in entity_spans[:5]:
    # strip to first 200 chars
    print(' ', span[:200])

# Check today_tasks section
idx = html.find('njTaskList')
if idx > 0:
    section = html[idx:idx+3000]
    print('\n--- njTaskList section snippet ---')
    print(section[:1500])
