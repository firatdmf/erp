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


from authentication.models import GoogleChatCredentials

class user_settings(View):
    template_name = "user_settings.html"

    def get(self, request):
        google_creds = None
        if request.user.is_authenticated:
            google_creds = GoogleChatCredentials.objects.filter(user=request.user).first()
            
        return render(request, self.template_name, {
            "google_creds": google_creds,
            "is_google_connected": google_creds is not None,
            "user": request.user
        })


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

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        from datetime import datetime, timedelta, time
        from django.utils import timezone
        from team.models import TeamTask, TeamMeeting
        from team.models import TeamMember
        from django.db.models import Q, Subquery, OuterRef, Value
        from django.utils.timezone import make_aware

        # Check if this is an AJAX request for tasks by date
        selected_date = request.GET.get('date')
        task_tab = request.GET.get('tab', 'myTasks')  # Default to myTasks
        
        if selected_date:
            try:
                # Convert string to date object
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                today = timezone.localdate()
                
                # Calculate start and end of the selected day for index-friendly range query
                # This allow DB to use specific datetime index instead of casting column to date
                day_start = make_aware(datetime.combine(date_obj, time.min))
                day_end = make_aware(datetime.combine(date_obj, time.max))

                # Get current user's member
                current_member = request.user.member if hasattr(request.user, 'member') else None
                current_user = request.user
                
                print(f"\n=== Dashboard AJAX Debug ===")
                print(f"Date: {date_obj}, Tab: {task_tab}")
                
                # Base query - date filtering
                if date_obj == today:
                    # If selected date is today, show all tasks up to and including today
                    # For index usage: due_date <= today
                    base_query = Task.objects.filter(completed=False, due_date__lte=today)
                else:
                    # For other dates, show range of that day
                    # Note: Task.due_date is distinct from TeamTask.due_date (date vs datetime)
                    # Task.due_date is DateField, so exact match is fine and indexed
                    base_query = Task.objects.filter(completed=False, due_date=date_obj)
                
                # Apply tab filter - only show myTasks for calendar
                if task_tab == 'myTasks':
                    # Include tasks where user is the member OR is in assignees
                    tasks = list(base_query.filter(
                        Q(member=current_member) | Q(assignees=current_member)
                    ).distinct().select_related('contact', 'company', 'member', 'member__user', 'created_by', 'created_by__user').order_by('-due_date'))
                    print(f"My Tasks count: {len(tasks)}")
                    
                    # Subquery to get current user's role in the task's team
                    user_role_subquery = TeamMember.objects.filter(
                        team=OuterRef('team'),
                        user=current_user
                    ).values('role')[:1]

                    # TeamTask filtering using Range for DatetimeField
                    if date_obj == today:
                         # For today, we want everything up to end of today
                        team_tasks_query = TeamTask.objects.filter(
                            assignees=current_user,
                            due_date__lte=day_end # Use range/lte on datetime index
                        ).exclude(status='done')
                    else:
                        # For specific day: Use RANGE to hit the index
                        team_tasks_query = TeamTask.objects.filter(
                            assignees=current_user,
                            due_date__range=(day_start, day_end)
                        ).exclude(status='done')
                    
                    # Annotate with user role for permission check without N+1
                    team_tasks = list(team_tasks_query.annotate(
                        current_user_role=user_role_subquery
                    ).distinct().select_related('team', 'assigned_to', 'assigned_by').prefetch_related('assignees').order_by('-due_date'))
                    print(f"Team Tasks count: {len(team_tasks)}")

                    # Fetch Team Meetings using Range for DatetimeField (Index Optimized)
                    meetings_query = TeamMeeting.objects.filter(
                        Q(team__members=current_user) | 
                        Q(participants=current_user) |
                        Q(organizer=current_user),
                        scheduled_at__range=(day_start, day_end)
                    ).select_related('organizer', 'team').prefetch_related('participants').order_by('scheduled_at').distinct()
                    
                    meetings = list(meetings_query)
                    print(f"Meetings count: {len(meetings)}")

                else:  # assignedTasks
                    tasks = list(base_query.filter(created_by=current_member).exclude(member=current_member).select_related('contact', 'company', 'member', 'member__user', 'created_by', 'created_by__user').order_by('-due_date'))
                    team_tasks = []
                    meetings = []
                    print(f"Assigned Tasks count: {len(tasks)}")
                    for t in tasks:
                        print(f"  - Task ID {t.id}: {t.name} -> {t.member}")
                print(f"========================\n")
                
                # Render tasks using the same template
                html = render_to_string('todo/components/tasks.html', {
                    'tasks': tasks,
                    'team_tasks': team_tasks if task_tab == 'myTasks' else [],
                    'meetings': meetings,
                    'sort_type': 'dictsortreversed',
                    'page_type': 'dashboard_calendar',
                    'csrf_token': request.META.get('CSRF_COOKIE'),
                    'path': request.path,
                    'member': request.user.member if hasattr(request.user, 'member') else None,
                    'request': request,
                })
                
                return HttpResponse(html)
            except ValueError:
                return HttpResponse('<div class="tasks_component"><ul><li style="color: red;">Invalid date format</li></ul></div>')
        
        return render(request, self.template_name, {"title": "Dashboard"})
    

    


# ------------------- Search Redesign -------------------

from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

class GlobalSearch(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        search_type = request.GET.get('type', 'all')
        results = []

        # If query is empty, we might want to return "Recent" items for specific tabs
        if not query or len(query) < 2:
            if search_type == 'products':
                from marketing.models import Product
                # Return last 50 products
                recent_products = Product.objects.all().order_by('-id')[:50]
                for p in recent_products:
                    try:
                        url = reverse('marketing:product_edit', args=[p.id])
                    except:
                        url = '#'
                    results.append({
                        'type': 'Product',
                        'name': p.title,
                        'detail': p.sku,
                        'url': url,
                        'icon': 'fa-box'
                    })
                return JsonResponse({'results': results})
            
            elif search_type == 'orders':
                from operating.models import Order
                # Return last 50 orders
                recent_orders = Order.objects.all().order_by('-id')[:50]
                for o in recent_orders:
                     try:
                        url = reverse('operating:order_detail', args=[o.id])
                     except:
                        url = '#'
                     results.append({
                        'type': 'Order',
                        'name': o.order_number or f"Order #{o.id}",
                        'detail': o.get_status_display(),
                        'url': url,
                        'icon': 'fa-shopping-cart'
                    })
                return JsonResponse({'results': results})
            
            # For other cases (all, contacts, etc.) return empty or let frontend handle defaults
            return JsonResponse({'results': []})

        limit = 50 if search_type != 'all' else 5

        # 1. Contacts (email and phone are ArrayFields, so we need special handling)
        if search_type in ['all', 'contacts']:
            # For ArrayFields, cast to text and use ILIKE for partial matching
            from django.db.models.functions import Cast
            from django.db.models import TextField
            contacts = Contact.objects.annotate(
                email_text=Cast('email', TextField()),
                phone_text=Cast('phone', TextField())
            ).filter(
                Q(name__icontains=query) |
                Q(email_text__icontains=query) |
                Q(phone_text__icontains=query)
            )[:limit]
            for c in contacts:
                try:
                    url = reverse('crm:contact_detail', args=[c.id])
                except:
                    url = '#'
                results.append({
                    'type': 'Contact',
                    'name': c.name,
                    'detail': c.email[0] if c.email else '',
                    'url': url,
                    'icon': 'fa-user'
                })

        # 2. Companies (email and phone are also ArrayFields)
        if search_type in ['all', 'contacts']:
            from django.db.models.functions import Cast
            from django.db.models import TextField
            companies = Company.objects.annotate(
                email_text=Cast('email', TextField()),
                phone_text=Cast('phone', TextField())
            ).filter(
                Q(name__icontains=query) |
                Q(email_text__icontains=query) |
                Q(phone_text__icontains=query)
            )[:limit]
            for c in companies:
                try:
                    url = reverse('crm:company_detail', args=[c.id])
                except:
                    url = '#'
                results.append({
                    'type': 'Company',
                    'name': c.name,
                    'detail': c.status,
                    'url': url,
                    'icon': 'fa-building'
                })

        # 3. Products
        if search_type in ['all', 'products']:
            from marketing.models import Product
            products = Product.objects.filter(
                Q(title__icontains=query) | Q(sku__icontains=query)
            )[:limit]
            for p in products:
                try:
                    url = reverse('marketing:product_edit', args=[p.id])
                except:
                    url = '#'
                results.append({
                    'type': 'Product',
                    'name': p.title,
                    'detail': p.sku,
                    'url': url,
                    'icon': 'fa-box'
                })
            
        # 4. Tasks (Todo) -- Mapped to 'orders' tab? No, maybe 'all' only or add 'tasks' tab. 
        # User didn't ask for task tab specifically but we have it.
        # Let's include in 'all' or if we add a 'search-tasks' tab. 
        # For now 'all' only unless user asks.
        if search_type == 'all':
            tasks = Task.objects.filter(name__icontains=query)[:5]
            for t in tasks:
                try:
                    url = reverse('todo:task_detail', args=[t.id])
                except:
                    url = '#'
                results.append({
                    'type': 'Task',
                    'name': t.name,
                    'detail': t.priority,
                    'url': url,
                    'icon': 'fa-check-circle'
                })
            
        # 5. Orders
        if search_type in ['all', 'orders']:
            from operating.models import Order
            order_filter = Q(order_number__icontains=query)
            # Only add id filter if query is numeric
            if query.isdigit():
                order_filter |= Q(id=int(query))
            orders = Order.objects.filter(order_filter)[:limit]
            for o in orders:
                 try:
                    url = reverse('operating:order_detail', args=[o.id])
                 except:
                    url = '#'
                 results.append({
                    'type': 'Order',
                    'name': o.order_number or f"Order #{o.id}",
                    'detail': o.get_status_display(),
                    'url': url,
                    'icon': 'fa-shopping-cart'
                })

        return JsonResponse({'results': results})

