from django.shortcuts import render, redirect
from django.http import HttpResponse,HttpResponseRedirect
from django.urls import reverse
from django import forms
from .models import Task
from django.http import HttpRequest

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
    template_name = "todo/index.html"
    # index here is from the url name
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class TaskReport(generic.ListView):
    # Model to list out
    model = Task
    # Where to list out
    template_name = "todo/task_report.html"
    # Variable to use in the template for listing out
    context_object_name = "tasks"



@method_decorator(login_required, name="dispatch")
class EditTaskView(generic.edit.UpdateView):
    model = Task
    form_class = TaskForm  # Your form class for editing the entry
    template_name = "todo/update_task.html"  # Template for editing an entry

    # success_url = "/todo/"  # URL to redirect after successfully editing an entry
    # Instead of doing like above, let's get the url to go to from the get variable in the url. 
    # To accomplish this I will pass the variable from the update_task.html template and set it equal to the success_url 
    def form_valid(self, form):
        next_url = self.request.POST.get('next_url')
        if(next_url):
            self.success_url = next_url
        else:
            self.success_url = '/todo/'
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
    # below line brings back the user to the current page
    return redirect(request.META.get("HTTP_REFERER"))


# @method_decorator(login_required, name="dispatch")
def delete_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        task.delete()
        # below line brings back the user to the current page
        return redirect(request.META.get("HTTP_REFERER"))
