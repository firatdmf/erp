from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from todo.models import Task
from crm.models import Contact, Company
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator

# def index(request):
#     return HttpResponse('<h1>Welcome to the ERP!</h1>')
#     # return render(request,'erp/index.html')


@method_decorator(login_required, name="dispatch")
class index(TemplateView):
    template_name = "index.html"


class reports(View):
    template_name = "reports.html"

    def get(self, request):
        return render(request, self.template_name)

class user_settings(TemplateView):
    template_name = "user_settings.html"


class task_report(View):
    template_name = "task_report.html"
    tasks = Task.objects

    def get_context_data(self, **kwargs):
        context = {}
        context["my_variable"] = 123
        context["tasks"] = Task.objects.all()
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)


class test_page(TemplateView):
    template_name = "test_page.html"

class test_page2(TemplateView):
    template_name = "test_page2.html"


# ------------------- Dashboard ------------------- below things do exactly the same thing.  Leaving this for your future reference

# def dashboard(request):
#     return render(request, "dashboard.html", {"title": "Dashboarsssd"})

# class Dashboard(TemplateView):
#     template_name = "dashboard.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["title"] = "Dashboasadszortzortadsadrd"
#         return context

class Dashboard(View):
    template_name = "dashboard.html"

    def get(self, request,*args, **kwargs):
        # Check if this is an AJAX request for tasks by date
        selected_date = request.GET.get('date')
        task_tab = request.GET.get('tab', 'myTasks')  # Default to myTasks
        
        if selected_date:
            from django.http import HttpResponse
            from django.template.loader import render_to_string
            from datetime import datetime
            from django.utils import timezone
            
            try:
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                today = timezone.localdate()
                
                # Get current user's member
                current_member = request.user.member if hasattr(request.user, 'member') else None
                print(f"\n=== Dashboard AJAX Debug ===")
                print(f"Date: {date_obj}, Tab: {task_tab}")
                print(f"Current member: {current_member} (ID: {current_member.id if current_member else None})")
                
                # Base query - date filtering
                if date_obj == today:
                    # If selected date is today, show all tasks up to and including today
                    base_query = Task.objects.filter(completed=False, due_date__lte=today)
                else:
                    # For other dates, show only tasks for that specific date
                    base_query = Task.objects.filter(completed=False, due_date=date_obj)
                
                print(f"Base query count: {base_query.count()}")
                
                # Apply tab filter
                if task_tab == 'myTasks':
                    tasks = base_query.filter(member=current_member).select_related('contact', 'company', 'member', 'created_by').order_by('-due_date')
                    print(f"My Tasks count: {tasks.count()}")
                else:  # assignedTasks
                    tasks = base_query.filter(created_by=current_member).exclude(member=current_member).select_related('contact', 'company', 'member', 'member__user', 'created_by').order_by('-due_date')
                    print(f"Assigned Tasks count: {tasks.count()}")
                    for t in tasks:
                        print(f"  - Task ID {t.id}: {t.name} -> {t.member}")
                print(f"========================\n")
                
                # Render tasks using the same template
                html = render_to_string('todo/components/tasks.html', {
                    'tasks': tasks,
                    'sort_type': 'dictsortreversed',
                    'page_type': 'dashboard_calendar',
                    'csrf_token': request.META.get('CSRF_COOKIE'),
                    'path': request.path,
                    'member': request.user.member if hasattr(request.user, 'member') else None,
                })
                
                return HttpResponse(html)
            except ValueError:
                return HttpResponse('<div class="tasks_component"><ul><li style="color: red;">Invalid date format</li></ul></div>')
        
        return render(request, self.template_name, {"title": "Dashboard"})
    

    
