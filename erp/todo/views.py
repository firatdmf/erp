from django.shortcuts import render, redirect
from django.http import HttpResponse,HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django import forms
from .models import Task
from django.http import HttpRequest
from django.utils import timezone
from django.template.loader import render_to_string

# Create your views here.
from django.views import generic, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from .forms import TaskForm
from django.http import JsonResponse
from .models import Contact, Company
from django.urls import reverse_lazy

# to make it only viewable to users
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


class task_list(generic.ListView):
    # Model to list out
    model = Task
    # Where to list out
    template_name = "todo/task_list.html"
    # Variable to use in the template for listing out
    context_object_name = "tasks"
    # ordering = '-created_at'

    # def get_queryset(self):
    #     # Get the current date
    #     current_date = date.today()

    #     # Calculate the days since due for each task
    #     queryset = super().get_queryset()
    #     for task in queryset:
    #         task.days_since_due = (current_date - task.due_date).days

    #     return queryset

    # def get_ordering(self):
    #     ordering = self.request.GET.get('ordering','-created_at')
    #     return ordering

    # def get_context_data(self, **kwargs):
    #     # get the current context data
    #     context = super().get_context_data(**kwargs)
    #     # add to it
    #     context["current_date"] = date.today()  # Add the current date to the context
    #     return context


# just a simple template view
@method_decorator(login_required, name="dispatch")
class index(View):
    def get(self, request):
        # Get the data from the task_list view
        task_list_view = task_list.as_view()
        task_list_data = task_list_view(request)
        task_list_context = task_list_data.context_data

        # Get the data from the CreateTask view
        create_task_view = CreateTask.as_view()
        create_task_data = create_task_view(request)
        create_task_context = create_task_data.context_data

        # Merge the context data from both views
        context = {**task_list_context, **create_task_context}

        # # Render the template with the combined context
        return render(request, "todo/index.html", context)

    def post(self, request):
        # Your code for handling POST requests
        # This part should process the submitted form data and save it

        form = TaskForm(request.POST)  # Bind the form with the POST data

        if form.is_valid():
            # Form is valid, save the task
            form.save()
            # You can also add a success message if needed
            # messages.success(request, 'Task created successfully.')

            # Redirect to a different URL (e.g., task list)
            return redirect("/todo")  # Adjust the URL name if needed

        # Form is not valid, re-render the page with form errors
        tasks = Task.objects.all()  # Fetch all tasks (adjust the queryset as needed)

        context = {
            "form": form,
            "tasks": tasks,
        }

        return render(request, "todo/index.html", context)


# -------------------------------------------------


@method_decorator(login_required, name="dispatch")
class CreateTask(generic.edit.CreateView):
    model = Task
    form_class = TaskForm
    template_name = "todo/create_task.html"
    # index here is from the url name
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        print("your member iss")
        print("your member is", self.request.user.member)
        print("Form due_date:", form.cleaned_data.get('due_date'))
        print("Current localdate:", timezone.localdate())
        print("Current date.today():", date.today())
        form.instance.created_by = self.request.user.member
        # If member is not set, assign to creator
        if not form.instance.member:
            form.instance.member = self.request.user.member
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class TaskReport(View):
    template_name = "todo/task_report.html"
    
    def get(self, request):
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        current_member = request.user.member if hasattr(request.user, 'member') else None
        tab = request.GET.get('tab', 'myTasks')
        search_query = request.GET.get('search', '').strip()
        page_number = request.GET.get('page', 1)
        
        print(f"\n=== TaskReport Debug ===")
        print(f"Current member: {current_member} (ID: {current_member.id if current_member else None})")
        print(f"Tab: {tab}")
        print(f"Search: {search_query}")
        print(f"Page: {page_number}")
        
        # My Tasks - tasks assigned to me (OPTIMIZED)
        my_tasks_query = Task.objects.filter(
            member=current_member,
            completed=False
        ).select_related(
            'contact', 
            'company', 
            'member__user',  # ✅ Optimized: member.user already loaded
            'created_by__user'
        ).order_by('-priority', 'due_date')
        
        # Apply search filter for My Tasks (OPTIMIZED - Türkçe karakter desteği ile)
        if search_query:
            # Türkçe karakterler için upper() kullan (İ/i problemi için)
            search_upper = search_query.upper()
            my_tasks_query = my_tasks_query.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(contact__name__icontains=search_query) |
                Q(company__name__icontains=search_query)
            )
        
        print(f"My tasks count: {my_tasks_query.count()}")
        
        # Paginate My Tasks
        my_tasks_paginator = Paginator(my_tasks_query, 10)  # 10 tasks per page
        my_tasks_page = my_tasks_paginator.get_page(page_number if tab == 'myTasks' else 1)
        
        # Assigned Tasks - tasks I created/assigned to others (OPTIMIZED)
        assigned_tasks_query = Task.objects.filter(
            created_by=current_member,
            completed=False
        ).exclude(
            member=current_member
        ).select_related(
            'contact', 
            'company', 
            'member__user',  # ✅ Already optimized
            'created_by__user'
        ).order_by('-priority', 'due_date')
        
        # Apply search filter for Assigned Tasks (OPTIMIZED - Türkçe karakter desteği ile)
        if search_query:
            # Türkçe karakterler için upper() kullan (İ/i problemi için)
            search_upper = search_query.upper()
            assigned_tasks_query = assigned_tasks_query.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(contact__name__icontains=search_query) |
                Q(company__name__icontains=search_query) |
                Q(member__user__first_name__icontains=search_query) |
                Q(member__user__last_name__icontains=search_query)
            )
        
        print(f"Assigned tasks count: {assigned_tasks_query.count()}")
        
        # Calculate statistics BEFORE applying search (for display purposes)
        # These should NOT change when user searches
        my_total_count = Task.objects.filter(member=current_member, completed=False).count()
        assigned_total_count = Task.objects.filter(
            created_by=current_member,
            completed=False
        ).exclude(member=current_member).count()
        
        # Paginate Assigned Tasks
        assigned_tasks_paginator = Paginator(assigned_tasks_query, 10)  # 10 tasks per page
        assigned_tasks_page = assigned_tasks_paginator.get_page(page_number if tab == 'assignedTasks' else 1)
        
        # AJAX için direkt döndür - statistics'i hesaplama (ÇOOK DAHA HIZLI)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if tab == 'myTasks':
                html = render_to_string('todo/components/task_table.html', {
                    'tasks': my_tasks_page,
                    'today': timezone.localdate(),
                    'total_count': my_total_count,  # Use pre-calculated total, not filtered count
                    'completed_count': 0,  # Skip expensive query
                    'ongoing_count': my_total_count,  # Use pre-calculated total
                    'is_assigned_view': False,
                    'search_query': search_query,
                    'tab': tab,
                }, request=request)
            else:
                html = render_to_string('todo/components/task_table.html', {
                    'tasks': assigned_tasks_page,
                    'today': timezone.localdate(),
                    'total_count': assigned_total_count,  # Use pre-calculated total, not filtered count
                    'completed_count': 0,  # Skip expensive query
                    'ongoing_count': assigned_total_count,  # Use pre-calculated total
                    'is_assigned_view': True,
                    'search_query': search_query,
                    'tab': tab,
                }, request=request)
            return HttpResponse(html)
        
        # Full page load için statistics hesapla
        from datetime import timedelta
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # My Tasks - all tasks assigned to me (including completed)
        all_my_tasks = Task.objects.filter(member=current_member)
        my_total = all_my_tasks.count()
        my_ongoing = all_my_tasks.filter(completed=False).count()
        my_completed_this_week = all_my_tasks.filter(
            completed=True,
            completed_at__gte=week_start,
            completed_at__lte=week_end + timedelta(days=1)  # Include end of Sunday
        ).count()
        
        # Assigned Tasks - all tasks I created for others (including completed)
        all_assigned_tasks = Task.objects.filter(
            created_by=current_member
        ).exclude(member=current_member)
        assigned_total = all_assigned_tasks.count()
        assigned_ongoing = all_assigned_tasks.filter(completed=False).count()
        assigned_completed_this_week = all_assigned_tasks.filter(
            completed=True,
            completed_at__gte=week_start,
            completed_at__lte=week_end + timedelta(days=1)
        ).count()
        
        context = {
            'my_tasks': my_tasks_page,
            'assigned_tasks': assigned_tasks_page,
            'current_member': current_member,
            'today': timezone.localdate(),
            'search_query': search_query,
            # My Tasks stats
            'my_total_count': my_total,
            'my_completed_count': my_completed_this_week,
            'my_ongoing_count': my_ongoing,
            # Assigned Tasks stats
            'assigned_total_count': assigned_total,
            'assigned_completed_count': assigned_completed_this_week,
            'assigned_ongoing_count': assigned_ongoing,
        }
        
        return render(request, self.template_name, context)


@method_decorator(login_required, name="dispatch")
class TasksList(View):
    template_name = "todo/tasks_list.html"
    
    def get(self, request):
        current_member = request.user.member if hasattr(request.user, 'member') else None
        
        # My Tasks - tasks assigned to me
        my_tasks = Task.objects.filter(
            member=current_member,
            completed=False
        ).select_related('contact', 'company', 'member').order_by('due_date')
        
        # Assigned Tasks - tasks I created/assigned to others (would need created_by field)
        # For now, show tasks assigned to other members
        from authentication.models import Member
        assigned_tasks = Task.objects.filter(
            completed=False
        ).exclude(
            member=current_member
        ).exclude(
            member__isnull=True
        ).select_related('contact', 'company', 'member').order_by('due_date')
        
        context = {
            'my_tasks': my_tasks,
            'assigned_tasks': assigned_tasks,
            'current_member': current_member,
            'today': timezone.localdate(),
        }
        
        return render(request, self.template_name, context)



@method_decorator(login_required, name="dispatch")
class EditTaskView(generic.edit.UpdateView):
    model = Task
    form_class = TaskForm  # Your form class for editing the entry
    template_name = "todo/update_task.html"  # Template for editing an entry

    # success_url = "/todo/"  # URL to redirect after successfully editing an entry
    # Instead of doing like above, let's get the url to go to from the get variable in the url. 
    # To accomplish this I will pass the variable from the update_task.html template and set it equal to the success_url 
    def form_valid(self, form):
        next_url = self.request.GET.get('next_url')
        if(next_url):
            self.success_url = next_url
            print("next_url",next_url)
        else:
            self.success_url = '/todo/'
            print("no next_url")
        return super().form_valid(form)


# def edit_task(request,pk):
#     task = get_object_or_404(Task,pk=pk)
#     if request.method == 'POST':
#         form = TaskForm(request.POST, instance=task)
#         if form.is_valid():
#             form.save()
#             return redirect('/todo/')  # Redirect to success URL
#     else:
#         form = TaskForm(instance=task)

#     return render(request, 'todo/update_task.html', {'form': form})


# class TaskUpdateView(generic.edit.UpdateView):
#     model = Task
#     form_class = TaskForm
#     template_name = 'todo/your_template.html'  # Replace 'your_template.html' with your actual template file

#     def get_object(self, queryset=None):
#         # Retrieve the Task object you want to edit based on its ID
#         return get_object_or_404(Task, pk=self.kwargs['pk'])

#     def get_context_data(self, **kwargs):
#         context = super(TaskUpdateView, self).get_context_data(**kwargs)
#         # You can add additional context data if needed
#         return context

#     def form_valid(self, form):
#         # Your logic for handling the form submission if it's valid
#         return super(TaskUpdateView, self).form_valid(form)

#     def get_success_url(self):
#         # Specify the URL to redirect to after a successful form submission
#         return redirect("/todo")  # Replace 'your_success_url_name' with your actual URL name


# @method_decorator(login_required, name="dispatch")
def search_contacts_and_companies(request):
    search_query = request.GET.get("search_query", "")

    # Query the database for contacts and companies with matching names
    matching_contacts = Contact.objects.filter(name__icontains=search_query)
    matching_companies = Company.objects.filter(name__icontains=search_query)

    # Serialize the suggestions as JSON
    # suggestions = list(matching_contacts.values_list('name', flat=True)) + list(matching_companies.values_list('name', flat=True))

    # Serialize the suggestions as JSON, including IDs
    contact_suggestions = [
        {
            "id": contact.id,
            "name": contact.name,
            "type": "contact",
        }
        for contact in matching_contacts
    ]
    company_suggestions = [
        {
            "id": company.id,
            "name": company.name,
            "type": "company",
        }
        for company in matching_companies
    ]

    suggestions = contact_suggestions + company_suggestions

    return JsonResponse({"suggestions": suggestions})


# @method_decorator(login_required, name="dispatch")
def complete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.completed = True
    task.completed_at = datetime.now()
    task.save()
    
    # Check if it's an AJAX/HTMX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return task data for history
        return JsonResponse({
            'success': True,
            'task': {
                'name': task.name,
                'description': task.description,
                'completed_at': task.completed_at.strftime('%b %d, %Y - %I:%M %p')
            }
        })
    
    # below line brings back the user to the current page
    return redirect(request.META.get("HTTP_REFERER"))


# @method_decorator(login_required, name="dispatch")
def delete_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        task.delete()
        
        # Check if it's an AJAX request (HTMX)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('HX-Request'):
            # Return empty response - HTMX will handle removal with hx-swap="outerHTML"
            response = HttpResponse()
            # Send custom header to trigger toast notification
            response['HX-Trigger'] = '{"showToast": {"message": "Task deleted successfully", "type": "success"}}'
            return response
        
        # Fallback for non-AJAX requests
        return redirect(request.META.get("HTTP_REFERER"))


# Get task edit form (AJAX endpoint)
def get_task_edit_form(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    form = TaskForm(instance=task)
    
    # Render the form template
    html = render_to_string('todo/components/task_edit_form.html', {
        'task': task,
        'form': form,
    }, request=request)
    
    return HttpResponse(html)


# Update task via AJAX
def update_task_ajax(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        
        # Check if it's a member assignment update
        member_id = request.POST.get('member_id')
        if member_id:
            from authentication.models import Member
            try:
                member = Member.objects.get(id=member_id)
                task.member = member
                task.save()
                return JsonResponse({'success': True})
            except Member.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Member not found'})
        
        # Get data from POST
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        due_date_str = request.POST.get('due_date', '').strip()
        priority = request.POST.get('priority', 'medium').strip()  # Default to medium if not provided
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Task name cannot be empty'})
        
        if not due_date_str:
            return JsonResponse({'success': False, 'error': 'Due date is required'})
        
        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if priority not in valid_priorities:
            priority = 'medium'  # Fallback to medium if invalid
        
        try:
            # Parse due date
            from datetime import datetime
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            
            # Update task
            task.name = name
            task.description = description
            task.due_date = due_date
            task.priority = priority  # Update priority
            task.save()
            
            # Calculate overdue display
            from datetime import date as dt_date
            delta = (due_date - dt_date.today()).days
            if delta < 0:
                overdue_badge = f'<span class="task-overdue">{abs(delta)}d</span>'
            elif delta == 0:
                overdue_badge = '<span class="task-overdue">today</span>'
            else:
                overdue_badge = ''
            
            return JsonResponse({
                'success': True,
                'task': {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'due_date': due_date.strftime('%b %d, %Y'),
                    'priority': task.priority,  # Include priority in response
                    'overdue_badge': overdue_badge
                }
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# Task detail full page view
@login_required
def task_detail_page(request, task_id):
    from authentication.models import Member
    
    task = get_object_or_404(Task, pk=task_id)
    task = Task.objects.select_related(
        'member', 'member__user',
        'created_by', 'created_by__user',
        'contact', 'company'
    ).prefetch_related('comments', 'comments__author', 'comments__author__user').get(pk=task_id)
    
    comments = task.comments.all().order_by('-created_at')
    all_members = Member.objects.select_related('user').all()
    
    context = {
        'task': task,
        'comments': comments,
        'all_members': all_members,
    }
    
    return render(request, 'todo/task_detail_page.html', context)


# Get task detail (AJAX endpoint)
@login_required
def task_detail_ajax(request, task_id):
    from datetime import date as dt_date
    task = get_object_or_404(Task, pk=task_id)
    
    # Get task with related data
    task = Task.objects.select_related(
        'member', 'member__user',
        'created_by', 'created_by__user',
        'contact', 'company'
    ).prefetch_related('comments', 'comments__author', 'comments__author__user').get(pk=task_id)
    
    # Check permissions
    can_edit = request.user.member == task.created_by or request.user.member == task.member
    
    # Prepare comments data
    comments_data = []
    for comment in task.comments.all().order_by('created_at'):
        comments_data.append({
            'id': comment.id,
            'author_name': f"{comment.author.user.first_name} {comment.author.user.last_name}",
            'content': comment.content,
            'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
        })
    
    # Check if overdue or today
    today = dt_date.today()
    is_overdue = task.due_date < today
    is_today = task.due_date == today
    
    # Prepare task data
    task_data = {
        'id': task.id,
        'name': task.name,
        'description': task.description or '',
        'priority': task.priority,
        'priority_display': task.get_priority_display(),
        'due_date': task.due_date.strftime('%b %d, %Y'),
        'is_overdue': is_overdue,
        'is_today': is_today,
        'completed': task.completed,
        'member_name': f"{task.member.user.first_name} {task.member.user.last_name}" if task.member else 'Unassigned',
        'created_by_name': f"{task.created_by.user.first_name} {task.created_by.user.last_name}" if task.created_by else 'Unknown',
        'contact_name': task.contact.name if task.contact else None,
        'contact_id': task.contact.id if task.contact else None,
        'company_name': task.company.name if task.company else None,
        'company_id': task.company.id if task.company else None,
        'can_edit': can_edit,
        'comments': comments_data
    }
    
    return JsonResponse({'success': True, 'task': task_data})


# Add comment to task
@login_required
def add_task_comment(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return HttpResponse('<div style="color: red;">Comment cannot be empty</div>', status=400)
        
        from .models import TaskComment
        from django.utils.timesince import timesince
        
        comment = TaskComment.objects.create(
            task=task,
            author=request.user.member,
            content=content
        )
        
        # Return HTML snippet for HTMX
        html = f'''
        <div class="comment-item" style="display: flex; gap: 1rem;">
            <div class="comment-avatar" style="flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.75rem;">
                {comment.author.user.first_name[0]}{comment.author.user.last_name[0]}
            </div>
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; color: #0f172a; font-size: 0.875rem;">{comment.author.user.first_name} {comment.author.user.last_name}</span>
                    <span style="font-size: 0.75rem; color: #94a3b8;">az önce</span>
                </div>
                <div style="color: #475569; font-size: 0.875rem; line-height: 1.6; white-space: pre-wrap;">{comment.content}</div>
            </div>
        </div>
        <script>
            // Remove empty state message if it exists
            const noComments = document.getElementById('noComments');
            if (noComments) noComments.remove();
        </script>
        '''
        
        return HttpResponse(html)
    
    return HttpResponse('Invalid request', status=400)
