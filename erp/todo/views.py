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

        # Bind the form with the POST data and FILES
        form = TaskForm(request.POST, request.FILES)

        if form.is_valid():
            # Form is valid, save the task
            task = form.save()
            
            # Handle Attachments
            if request.FILES.getlist('attachments'):
                from erp.google_drive import upload_file_to_drive
                from .models import TaskAttachment
                
                for file_item in request.FILES.getlist('attachments'):
                    upload_result = upload_file_to_drive(request.user, file_item, folder_name="ERP Personal Tasks")
                    
                    if upload_result.get('success'):
                        TaskAttachment.objects.create(
                            task=task,
                            file_name=upload_result.get('name'),
                            drive_file_id=upload_result.get('file_id'),
                            drive_link=upload_result.get('drive_link'),
                            uploaded_by=request.user.member
                        )
                    else:
                        print(f"Failed to upload attachment {file_item.name}: {upload_result.get('error')}")

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
    # Redirect will be handled in form_valid to go to task detail page

    def post(self, request, *args, **kwargs):
        # Handle empty member field (common when creating personal tasks via sidebar)
        if 'member' in request.POST and not request.POST['member']:
            # Create a mutable copy of POST data
            post_data = request.POST.copy()
            # Set default member to current user
            if hasattr(request.user, 'member'):
                post_data['member'] = request.user.member.id
            request.POST = post_data
            
        return super().post(request, *args, **kwargs)

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
        response = super().form_valid(form)
        print("Task created:", self.object)
        
        # Handle multiple assignees
        assigned_ids_str = self.request.POST.get('assigned_users')
        if assigned_ids_str:
            try:
                from authentication.models import Member
                ids = [int(id_str) for id_str in assigned_ids_str.split(',') if id_str.strip()]
                if ids:
                    members = Member.objects.filter(id__in=ids)
                    self.object.assignees.set(members)
                    print(f"Assigned members: {members}")
            except Exception as e:
                print(f"Error setting assignees: {e}")

        files = self.request.FILES.getlist('task_files')
        
        if files:
            try:
                from erp.google_drive import upload_file_to_drive
                from .models import TaskAttachment
                
                for file_item in files:
                    print(f"Uploading {file_item.name}...")
                    upload_result = upload_file_to_drive(self.request.user, file_item, folder_name="ERP Personal Tasks")
                    print(f"Upload result: {upload_result}")
                    
                    if upload_result.get('success'):
                        TaskAttachment.objects.create(
                            task=self.object,
                            file_name=upload_result.get('name'),
                            drive_file_id=upload_result.get('file_id'),
                            drive_link=upload_result.get('drive_link'),
                            uploaded_by=self.request.user.member
                        )
                    else:
                        print(f"Failed to upload attachment {file_item.name}: {upload_result.get('error')}")
            except Exception as e:
                print(f"EXCEPTION in attachment handling: {e}")
                # Don't crash, just log
                
        # Push to Google Tasks
        try:
            from .google_tasks import push_task_to_google
            push_task_to_google(self.request.user, self.object)
        except Exception as e:
            print(f"Error pushing new task to Google Tasks: {e}")
                    
        return response

    def form_invalid(self, form):
        print("Form Invalid!")
        print(form.errors)
        return super().form_invalid(form)
    
    def get_success_url(self):
        # Redirect to task detail page after creation
        return reverse('todo:task_detail', kwargs={'task_id': self.object.pk})


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
        try:
            from .google_tasks import update_task_in_google
            update_task_in_google(self.request.user, form.instance)
        except Exception as e:
            print(f"Error updating task in Google Tasks: {e}")
            
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
    """Update task status - supports todo, in_progress, review, done"""
    task = get_object_or_404(Task, pk=task_id)
    
    # Get status from POST data
    status = request.POST.get('status')
    if not status:
        # Fallback for old calls or toggles
        status = 'done' if not task.completed else 'todo'
        
    old_status = task.status
    
    # Update task based on status
    task.status = status
    
    # Sync legacy fields
    if status == 'done':
        task.completed = True
        task.on_hold = False
        if not task.completed_at:
            task.completed_at = timezone.now()
        new_status_display = 'Done'
        activity_type = 'completed'
    elif status == 'review':
        task.completed = False
        task.on_hold = False # Review is active state
        task.completed_at = None
        new_status_display = 'Review'
        activity_type = 'status_changed'
    elif status == 'in_progress':
        task.completed = False
        task.on_hold = False
        task.completed_at = None
        new_status_display = 'In Progress'
        activity_type = 'reopened' if old_status == 'done' else 'status_changed'
    else:  # todo
        task.completed = False
        task.on_hold = False
        task.completed_at = None
        new_status_display = 'To Do'
        activity_type = 'status_changed'
    
    task.save()
    
    # Track activity
    from .models import TaskActivity
    current_user = request.user.member if hasattr(request.user, 'member') else None
    
    if old_status != status:
        TaskActivity.objects.create(
            task=task, user=current_user, activity_type=activity_type,
            old_value=old_status.replace('_', ' ').title(),
            new_value=new_status_display
        )
    
    # Check if it's an AJAX/HTMX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    if is_ajax or is_htmx:
        return JsonResponse({
            'success': True,
            'status': status,
            'status_display': new_status_display,
            'task': {
                'name': task.name,
                'description': task.description,
                'completed_at': task.completed_at.strftime('%b %d, %Y - %I:%M %p') if task.completed_at else None
            }
        })
    
    
    # Sync status to Google Tasks
    try:
        from .google_tasks import update_task_in_google
        update_task_in_google(request.user, task)
    except Exception as e:
        print(f"Error updating task completion in Google Tasks: {e}")
    
    # below line brings back the user to the current page
    return redirect(request.META.get("HTTP_REFERER"))


# @method_decorator(login_required, name="dispatch")
def delete_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        
        # Permission Check: Only creator can delete
        current_member = request.user.member if hasattr(request.user, 'member') else None
        if task.created_by != current_member:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Permission denied. Only the creator can delete this task.'}, status=403)
            return HttpResponse("Permission denied", status=403)

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
    task = get_object_or_404(
        Task.objects.select_related(
            'contact', 'company', 'member', 'member__user'
        ).prefetch_related(
            'assignees', 'assignees__user', 'attachments'
        ), 
        pk=task_id
    )
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
                
                # Sync legacy member to assignees if needed
                if not task.assignees.exists() and task.member:
                    task.assignees.add(task.member)
                
                # Add new member to assignees
                task.assignees.add(member)
                
                # Update legacy field as primary/latest
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
            
            # Save old values before updating (for activity tracking)
            old_due_date = task.due_date
            old_name = task.name
            old_description = task.description
            old_priority = task.priority
            
            # Update task
            task.name = name
            task.description = description
            task.due_date = due_date
            task.priority = priority  # Update priority
            task.save()
            
            # Track activities
            from .models import TaskActivity
            current_user = request.user.member if hasattr(request.user, 'member') else None
            
            if old_name != name:
                TaskActivity.objects.create(
                    task=task, user=current_user, activity_type='name_updated',
                    old_value=old_name, new_value=name
                )
            
            if old_description != description:
                TaskActivity.objects.create(
                    task=task, user=current_user, activity_type='description_updated',
                    old_value=old_description[:100] if old_description else None,
                    new_value=description[:100] if description else None
                )
            
            if old_priority != priority:
                TaskActivity.objects.create(
                    task=task, user=current_user, activity_type='priority_changed',
                    old_value=old_priority, new_value=priority
                )
            
            if old_due_date != due_date:
                TaskActivity.objects.create(
                    task=task, user=current_user, activity_type='due_date_changed',
                    old_value=old_due_date.strftime('%Y-%m-%d'),
                    new_value=due_date.strftime('%Y-%m-%d')
                )
            
            # Handle Assignees List (from Edit Sidebar)
            assigned_users_str = request.POST.get('assigned_users')
            if assigned_users_str is not None:
                from authentication.models import Member
                try:
                    # Store old assignees before updating
                    old_assignees = set(task.assignees.all())
                    
                    ids = [int(x) for x in assigned_users_str.split(',') if x.strip()]
                    if ids:
                        members = Member.objects.filter(user__id__in=ids)
                        task.assignees.set(members)
                        # Sync legacy member if needed (e.g. if currently empty or just to keep it valid)
                        # If task.member is not in new list, maybe we should switch it?
                        # For now, if task.member is null, set it.
                        if not task.member and members.exists():
                            task.member = members.first()
                        
                        # Detect newly added assignees and send notifications
                        new_assignees = set(members)
                        added_assignees = new_assignees - old_assignees
                        
                        if added_assignees:
                            from notifications.models import Notification
                            for member in added_assignees:
                                # Don't notify the user making the change
                                if current_user and member.id != current_user.id:
                                    Notification.create_notification(
                                        recipient=member,
                                        notification_type='task_assigned',
                                        title=f'Task Assigned: {task.name}',
                                        message=f'You have been assigned to "{task.name}" by {request.user.get_full_name() or request.user.username}',
                                        link=f'/todo/tasks/{task.id}/detail/',
                                        icon='fa-tasks',
                                        content_object=task
                                    )
                    else:
                        task.assignees.clear()
                except Exception as e:
                    print(f"Error updating assignees: {e}")

            # Handle File Uploads
            files = request.FILES.getlist('task_files')
            if files:
                try:
                    from erp.google_drive import upload_file_to_drive
                    from .models import TaskAttachment
                    
                    for file_item in files:
                        upload_result = upload_file_to_drive(request.user, file_item, folder_name="ERP Personal Tasks")
                        if upload_result.get('success'):
                            TaskAttachment.objects.create(
                                task=task,
                                file_name=upload_result.get('name'),
                                drive_file_id=upload_result.get('file_id'),
                                drive_link=upload_result.get('drive_link'),
                                uploaded_by=request.user.member if hasattr(request.user, 'member') else None
                            )
                except Exception as e:
                    print(f"Error uploading files: {e}")

            # Calculate overdue display (use same classes as tasks.html)
            from datetime import date as dt_date
            delta = (due_date - dt_date.today()).days
            if delta < 0:
                overdue_badge = f'<span class="badge badge-overdue">{abs(delta)}D</span>'
            elif delta == 0:
                overdue_badge = '<span class="badge badge-today">TODAY</span>'
            else:
                overdue_badge = ''
            
            return JsonResponse({
                'success': True,
                'task': {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'due_date': due_date.strftime('%b %d, %Y'),
                    'due_date_iso': due_date.strftime('%Y-%m-%d'),  # For calendar sync
                    'old_due_date_iso': old_due_date.strftime('%Y-%m-%d'),  # For calendar sync
                    'priority': task.priority,  # Include priority in response
                    'overdue_badge': overdue_badge
                }
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def delete_task_attachment(request, att_id):
    if request.method == "POST":
        from .models import TaskAttachment
        att = get_object_or_404(TaskAttachment, pk=att_id)
        att.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


# Task detail full page view
@login_required
def task_detail_page(request, task_id):
    from authentication.models import Member
    from .models import TaskActivity
    
    task = get_object_or_404(
        Task.objects.select_related(
            'member', 'member__user',
            'created_by', 'created_by__user',
            'contact', 'company'
        ).prefetch_related(
            'comments', 'comments__author', 'comments__author__user',
            'activities', 'activities__user', 'activities__user__user',
            'attachments', 'assignees'
        ),
        pk=task_id
    )
    
    comments = task.comments.all().order_by('-created_at')
    activities = task.activities.all().order_by('-created_at')[:50]  # Last 50 activities
    all_members = Member.objects.select_related('user').all()
    
    context = {
        'task': task,
        'comments': comments,
        'activities': activities,
        'all_members': all_members,
    }
    
    return render(request, 'todo/task_detail_page.html', context)


# Get task detail (AJAX endpoint)
@login_required
def task_detail_ajax(request, task_id):
    from datetime import date as dt_date
    
    # Get task with related data
    task = get_object_or_404(
        Task.objects.select_related(
            'member', 'member__user',
            'created_by', 'created_by__user',
            'contact', 'company'
        ).prefetch_related('comments', 'comments__author', 'comments__author__user'),
        pk=task_id
    )
    
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
        from django.utils.html import escape
        
        comment = TaskComment.objects.create(
            task=task,
            author=request.user.member,
            content=content
        )
        
        # Escape content to prevent XSS
        safe_content = escape(comment.content)
        
        # Get author info
        first_name = comment.author.user.first_name or ''
        last_name = comment.author.user.last_name or ''
        initials = f"{first_name[:1]}{last_name[:1]}"
        full_name = f"{first_name} {last_name}".strip() or "User"
        
        # Return HTML snippet for HTMX matching modern design
        html = f'''
        <div class="comment-row" style="animation: fadeIn 0.3s ease;">
            <div class="comment-avatar">{initials}</div>
            <div class="comment-main">
                <div class="comment-meta">
                    <span class="comment-author">{full_name}</span>
                    <span class="comment-time">just now</span>
                </div>
                <div class="comment-text">{safe_content}</div>
            </div>
        </div>
        <style>
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
        <script>
            // Remove empty state message if it exists
            const noComments = document.getElementById('noComments');
            if (noComments) noComments.remove();
        </script>
        '''
        
        return HttpResponse(html)
    
    return HttpResponse('Invalid request', status=400)
