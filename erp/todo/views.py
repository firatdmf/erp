from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from .models import Task

# Create your views here.
from django.views import generic, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from .forms import TaskForm
from django.http import JsonResponse
from .models import Contact, Company


class task_list(generic.ListView):
    # Model to list out
    model = Task
    # Where to list out
    template_name = "todo/task_list.html"
    # Variable to use in the template for listing out
    context_object_name = "tasks"
    # ordering = '-created_at'

    def get_queryset(self):
        # Get the current date
        current_date = date.today()

        # Calculate the days since due for each task
        queryset = super().get_queryset()
        for task in queryset:
            task.days_since_due = (current_date - task.due_date).days

        return queryset

    # def get_ordering(self):
    #     ordering = self.request.GET.get('ordering','-created_at')
    #     return ordering
    def get_context_data(self, **kwargs):
        # get the current context data
        context = super().get_context_data(**kwargs)
        # add to it
        context["current_date"] = date.today()  # Add the current date to the context
        return context


class CreateTask(generic.edit.CreateView):
    model = Task
    form_class = TaskForm
    template_name = "todo/index.html"
    # index here is from the url name
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        return super().form_valid(form)


def search_contacts_and_companies(request):
    search_query = request.GET.get("search_query", "")

    # Query the database for contacts and companies with matching names
    matching_contacts = Contact.objects.filter(name__icontains=search_query)
    matching_companies = Company.objects.filter(name__icontains=search_query)

    # Serialize the suggestions as JSON
    # suggestions = list(matching_contacts.values_list('name', flat=True)) + list(matching_companies.values_list('name', flat=True))

    # Serialize the suggestions as JSON, including IDs
    contact_suggestions = [
        {"id": contact.id, "name": contact.name, "type":"contact",} for contact in matching_contacts
    ]
    company_suggestions = [
        {"id": company.id, "name": company.name, "type":"company",} for company in matching_companies
    ]

    suggestions = contact_suggestions + company_suggestions

    return JsonResponse({"suggestions": suggestions})


# just a simple template view
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


def complete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.completed = True
    task.completed_at = datetime.now()
    task.save()
    return redirect("/todo")


def delete_task(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)
        task.delete()
        return redirect("/todo")
